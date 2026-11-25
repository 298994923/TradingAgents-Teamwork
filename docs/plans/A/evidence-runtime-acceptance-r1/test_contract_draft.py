"""Review-only cross-component samples and oracle checks, NOT graph/CLI acceptance.

Actual Evidence registration/save/load and E's low-level recorder are used.
Hand-built state/envelopes exercise the draft oracle only. Neither actual graph
capture nor CLI forwarding, reservation or path preparation is exercised here.
"""
import copy
import json
import socket
from dataclasses import replace
from pathlib import Path

import pytest
from assertions import assert_fresh_capture, assert_no_published_reference

from tradingagents.evidence import (
    EvidenceError,
    artifact_key_for,
    assess_replay,
    register_reports,
    save_snapshot,
)
from tradingagents.run_recorder import RunEvent, read_manifest, write_manifest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """A-EV-01: draft samples use local files and deny Python network calls."""
    def refuse(*args, **kwargs):
        raise AssertionError("Runtime acceptance drafts must not reach the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


@pytest.fixture
def inputs():
    return json.loads(Path(__file__).with_name("inputs.json").read_text(encoding="utf-8"))


def registration(inputs, variant):
    return {"selected_analysts": inputs["selected_analysts"],
            "analyst_outputs": copy.deepcopy(inputs["analyst_outputs"]),
            "source_run_id": inputs["runs"][variant], "captured_at": inputs["captured_at"],
            "context": copy.deepcopy(inputs["context"])}


def sample(inputs, tmp_path, variant="v0"):
    """Explicitly synthetic state; future runtime tests must supply observed state."""
    result = register_reports(**registration(inputs, variant))
    snapshot = result.snapshot
    key = artifact_key_for(snapshot.snapshot_id)
    root = tmp_path / variant / "evidence-store"
    destination = root / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    saved = save_snapshot(snapshot, destination)
    assert saved.status == "created"
    reference = {"snapshot_id": snapshot.snapshot_id, "artifact_key": key, "store": "local-fs",
                 "source_run_id": snapshot.source_run_id, "captured_at": snapshot.captured_at}
    state = {"evidence_snapshot": reference}
    event = RunEvent(
        run_id=inputs["runs"][variant], created_at="2026-11-25T08:01:00+00:00",
        version="synthetic-acceptance-inputs", ticker=inputs["ticker"],
        trade_date=inputs["trade_date"], asset_type="stock", outcome=None,
        config_snapshot={"workflow_variant": variant}, prompt_hashes={},
        evidence_snapshot=copy.deepcopy(reference), usage={}, duration_seconds=None,
        failure=None, stop_reason=None,
    )
    manifest = write_manifest(event, tmp_path / variant / "manifest.json")
    return {"result": result, "snapshot": snapshot, "state": state, "event": event,
            "root": root, "destination": destination, "manifest": manifest}


def check(inputs, bundle, variant="v0", **overrides):
    return assert_fresh_capture(
        final_state=bundle["state"], manifest_path=bundle["manifest"],
        artifact_root=bundle["root"], expected_run_id=inputs["runs"][variant],
        expected_capture_time=inputs["captured_at"],
        expected_reports=overrides.get("expected_reports", inputs["analyst_outputs"]),
        expected_context=inputs["context"],
    )


@pytest.mark.parametrize("variant", ["v0", "v1"])
def test_contract_sample_uses_real_artifact_and_recorder(inputs, tmp_path, variant):
    """A-EV-01/02/05/08: sample serialization only; not real V0/V1 graph runs."""
    bundle = sample(inputs, tmp_path, variant)
    loaded = check(inputs, bundle, variant)
    assert loaded.snapshot_id == bundle["snapshot"].snapshot_id
    assert read_manifest(bundle["manifest"])["schema_version"] == 1


@pytest.mark.parametrize("mutation", ["manifest_reference", "manifest_run_id", "both_capture_times"])
def test_oracle_rejects_reference_or_identity_drift(inputs, tmp_path, mutation):
    """A-EV-02/05: catch drift even when state and manifest share the wrong value."""
    bundle = sample(inputs, tmp_path)
    data = json.loads(bundle["manifest"].read_text())
    if mutation == "manifest_reference":
        data["evidence_snapshot"]["source_run_id"] = "different-source"
    elif mutation == "manifest_run_id":
        data["run_id"] = "different-run"
    else:
        changed = "2026-11-25T09:00:00.000000Z"
        data["evidence_snapshot"]["captured_at"] = changed
        bundle["state"]["evidence_snapshot"]["captured_at"] = changed
    bundle["manifest"].write_text(json.dumps(data))
    with pytest.raises(AssertionError):
        check(inputs, bundle)


def test_oracle_rejects_internally_valid_but_unexpected_report(inputs, tmp_path):
    """A-EV-02/05: a consistent self-hashed artifact can still hold the wrong input."""
    changed = copy.deepcopy(inputs)
    changed["analyst_outputs"]["news"] = "Wrong but internally consistent report."
    bundle = sample(changed, tmp_path)
    with pytest.raises(AssertionError, match="report content changed"):
        check(inputs, bundle)


def test_oracle_requires_an_actual_matching_artifact(inputs, tmp_path):
    """A-EV-05: matching non-null state/manifest dictionaries are insufficient."""
    bundle = sample(inputs, tmp_path)
    bundle["destination"].unlink()
    with pytest.raises(EvidenceError) as error:
        check(inputs, bundle)
    assert error.value.code == "IO_ERROR"
    assert isinstance(error.value.__cause__, FileNotFoundError)


def test_incomplete_sample_retains_diagnostics_and_is_not_replay_ready(inputs, tmp_path):
    """A-EV-06/07: a published reference is not proof of report completeness."""
    changed = copy.deepcopy(inputs)
    changed["analyst_outputs"].pop("news")
    changed["analyst_outputs"]["social"] = " \t\n"
    bundle = sample(changed, tmp_path)
    codes = {item.code for item in bundle["result"].diagnostics}
    assert {"MISSING_REPORT", "EMPTY_REPORT"} <= codes
    assessment = assess_replay(bundle["snapshot"], required_analysts=inputs["selected_analysts"],
                               expected_context=inputs["context"])
    assert assessment.ready is False
    snapshot = bundle["snapshot"]
    expected = {k: changed["analyst_outputs"].get(k) for k in inputs["selected_analysts"]}
    check(inputs, bundle, expected_reports=expected)
    assert snapshot.reports["news"].content is None


def test_null_sample_is_only_accepted_when_explicitly_expected(inputs, tmp_path):
    """A-EV-05/06: recorder null capability does not satisfy successful capture."""
    bundle = sample(inputs, tmp_path)
    event = replace(bundle["event"], evidence_snapshot=None)
    path = write_manifest(event, tmp_path / "disabled" / "manifest.json")
    state = {"evidence_snapshot": None}
    assert_no_published_reference(final_state=state, manifest_path=path)
    bundle.update(state=state, manifest=path)
    with pytest.raises(AssertionError, match="no state reference"):
        check(inputs, bundle)


def test_fixture_variants_compare_report_content_not_snapshot_identity(inputs, tmp_path):
    """A-EV-02: synthetic V0/V1 records differ in run metadata, not report inputs."""
    left, right = (sample(inputs, tmp_path, variant) for variant in ("v0", "v1"))
    assert left["snapshot"].snapshot_id != right["snapshot"].snapshot_id
    assert left["snapshot"].reports == right["snapshot"].reports
