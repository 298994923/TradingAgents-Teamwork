"""Offline tests for E's fresh V0/V1 evidence integration.

Covers four E-owned changes in ``cli/run.py`` and the new
``tradingagents/evidence_store.py``:

1. ``reserve_run_id`` reserves a collision-safe run directory up front; the
   manifest writer reuses that exact id (no re-reservation, no second mkdir).
2. ``write_run_manifest`` / ``_make_manifest_writer`` accept an optional
   ``run_id``; a supplied id is validated and reused as-is.
3. ``evidence_destination`` places A's canonical artifact key under
   ``<results>/runs/<run_id>/evidence/`` and refuses absolute / ``..`` / symlink
   escapes.
4. The evidence reference (``evidence_snapshot``) flows from the graph's final
   state into the manifest and the ``evidence-mode.json`` ``snapshot_ref``;
   a legitimate ``None`` stays ``None``.

No model, no network, no ``.env``.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import cli.run as cli_run  # noqa: E402
from tradingagents import evidence_store  # noqa: E402
from tradingagents.run_recorder import read_manifest  # noqa: E402

FIXED_AT = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
DIGEST = "0123456789abcdef" * 4
ARTIFACT_KEY = "v1/" + DIGEST + ".json"
SNAPSHOT_ID = "sha256:" + DIGEST


def _config(tmp_path):
    return {
        "results_dir": str(tmp_path),
        "llm_provider": "openai",
        "quick_think_llm": "gpt-6-luna",
        "deep_think_llm": "gpt-6-sol",
        "output_language": "English",
    }


# --- 1. reserve_run_id: collision-safe, distinct ids ------------------------


def test_reserve_run_id_returns_distinct_ids_for_same_inputs(tmp_path):
    config = _config(tmp_path)
    kwargs = {
        "config": config, "variant": "v0", "ticker": "NVDA",
        "trade_date": "2026-11-20", "repeat": 1, "at": FIXED_AT,
    }
    first = cli_run.reserve_run_id(**kwargs)
    second = cli_run.reserve_run_id(**kwargs)
    assert first != second
    assert (tmp_path / "runs" / first).is_dir()
    assert (tmp_path / "runs" / second).is_dir()


def test_reserve_run_id_creates_directory(tmp_path):
    run_id = cli_run.reserve_run_id(
        config=_config(tmp_path), variant="v1", ticker="NVDA",
        trade_date="2026-11-20", repeat=1, at=FIXED_AT,
    )
    assert run_id.startswith("v1-nvda-2026-11-20-r1-")
    assert (tmp_path / "runs" / run_id).is_dir()


# --- 2. writer reuses supplied run_id ---------------------------------------


def _write(tmp_path, **overrides):
    kwargs = {
        "config": _config(tmp_path), "ticker": "NVDA", "trade_date": "2026-11-20",
        "asset_type": "stock", "outcome": "Buy",
        "usage": {"llm_calls": 1, "tool_calls": 0, "tokens_in": 1, "tokens_out": 0},
        "duration_seconds": 1.0, "failure": None, "variant": "v0", "repeat": 1,
        "at": FIXED_AT, "version": "0.7.1",
    }
    kwargs.update(overrides)
    return cli_run.write_run_manifest(**kwargs)


def test_writer_reuses_supplied_run_id(tmp_path):
    run_id = cli_run.reserve_run_id(
        config=_config(tmp_path), variant="v0", ticker="NVDA",
        trade_date="2026-11-20", repeat=1, at=FIXED_AT,
    )
    path = _write(tmp_path, run_id=run_id)
    # Same id, no "-2" suffix; manifest lives under the reserved directory.
    assert path.parent.name == run_id
    assert read_manifest(path)["run_id"] == run_id


def test_writer_rejects_invalid_supplied_run_id(tmp_path):
    with pytest.raises(ValueError):
        _write(tmp_path, run_id="Bad/ID")


def test_writer_without_run_id_keeps_legacy_reservation(tmp_path):
    path = _write(tmp_path)
    assert path.parent.name.startswith("v0-nvda-2026-11-20-r1-")


# --- 2b. failure path reuses the SAME reservation ---------------------------


class _RaisingGraph:
    def __init__(self, evidence=None):
        self.evidence = evidence
        self.recorded = False
        self.cleared = False

    def record_decision(self, *a, **k):
        self.recorded = True

    def clear_checkpoint_on_success(self, *a, **k):
        self.cleared = True


def test_failure_path_reuses_same_reservation(tmp_path):
    run_id = cli_run.reserve_run_id(
        config=_config(tmp_path), variant="v0", ticker="NVDA",
        trade_date="2026-11-20", repeat=1, at=FIXED_AT,
    )

    class _Stats:
        def get_stats(self):
            return {"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0}

    selections = {"ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock"}
    write = cli_run._make_manifest_writer(
        _config(tmp_path), selections, _Stats(), started_at=0.0, variant="v0", run_id=run_id,
    )
    graph = _RaisingGraph()
    with pytest.raises(RuntimeError, match="boom"):
        cli_run._finalize_run_manifest(
            write=write, graph=graph, ticker="NVDA", trade_date="2026-11-20",
            asset_type="stock", portfolio=None, final_state=None,
            failure=RuntimeError("boom"),
        )
    manifest_path = tmp_path / "runs" / run_id / "manifest.json"
    assert manifest_path.is_file()
    assert read_manifest(manifest_path)["failure"] == "boom"
    # No second directory was created beside the reservation.
    assert not (tmp_path / "runs" / f"{run_id}-2").exists()


# --- 3. evidence_store containment -------------------------------------------


def test_evidence_destination_places_canonical_key_under_run(tmp_path):
    config = _config(tmp_path)
    dest = evidence_store.evidence_destination(config, "v0-nvda-2026-11-20-r1-x", ARTIFACT_KEY)
    expected_root = tmp_path / "runs" / "v0-nvda-2026-11-20-r1-x" / "evidence"
    assert dest == expected_root / "v1" / (DIGEST + ".json")
    assert dest.parent.is_dir()


@pytest.mark.parametrize("bad_key", [
    "/etc/passwd",
    "../escape.json",
    "v1/../" + DIGEST + ".json",
    "v1\\" + DIGEST + ".json",
    "v2/" + DIGEST + ".json",
    "v1/" + DIGEST.upper() + ".json",
    "v1/" + "a" * 63 + ".json",
    "",
], ids=["absolute", "dotdot", "traversal", "backslash", "wrong-version",
        "uppercase-hex", "short", "empty"])
def test_evidence_destination_rejects_non_canonical_keys(tmp_path, bad_key):
    with pytest.raises(ValueError):
        evidence_store.evidence_destination(_config(tmp_path), "v0-nvda-2026-11-20-r1-x", bad_key)


def test_evidence_destination_rejects_symlink_escape(tmp_path):
    run_id = "v0-nvda-2026-11-20-r1-x"
    evidence_root = tmp_path / "runs" / run_id / "evidence"
    evidence_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    # Make evidence/v1 a symlink pointing outside the run directory.
    (evidence_root / "v1").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        evidence_store.evidence_destination(_config(tmp_path), run_id, ARTIFACT_KEY)


def test_evidence_store_does_not_import_cli_run():
    source = Path(evidence_store.__file__).read_text(encoding="utf-8")
    assert "import cli.run" not in source
    assert "from cli.run" not in source


# --- 4. evidence reference forwarding ---------------------------------------


def test_populated_evidence_reference_forwarded_to_manifest_and_sidecar(tmp_path):
    run_id = cli_run.reserve_run_id(
        config=_config(tmp_path), variant="v0", ticker="NVDA",
        trade_date="2026-11-20", repeat=1, at=FIXED_AT,
    )
    reference = {"snapshot_id": SNAPSHOT_ID, "artifact_key": ARTIFACT_KEY}

    class _Stats:
        def get_stats(self):
            return {"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0}

    selections = {"ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock"}
    write = cli_run._make_manifest_writer(
        _config(tmp_path), selections, _Stats(), started_at=0.0, variant="v0", run_id=run_id,
    )
    graph = _RaisingGraph()
    cli_run._finalize_run_manifest(
        write=write, graph=graph, ticker="NVDA", trade_date="2026-11-20",
        asset_type="stock", portfolio=None,
        final_state={"evidence_snapshot": reference, "final_rating": "Buy"},
        failure=None,
    )
    run_dir = tmp_path / "runs" / run_id
    manifest = read_manifest(run_dir / "manifest.json")
    assert manifest["evidence_snapshot"] == reference
    sidecar = json.loads((run_dir / "evidence-mode.json").read_text(encoding="utf-8"))
    assert sidecar["snapshot_ref"] == {"snapshot_id": SNAPSHOT_ID, "artifact_key": ARTIFACT_KEY}


def test_null_evidence_reference_stays_null(tmp_path):
    run_id = cli_run.reserve_run_id(
        config=_config(tmp_path), variant="v0", ticker="NVDA",
        trade_date="2026-11-20", repeat=1, at=FIXED_AT,
    )

    class _Stats:
        def get_stats(self):
            return {"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0}

    selections = {"ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock"}
    write = cli_run._make_manifest_writer(
        _config(tmp_path), selections, _Stats(), started_at=0.0, variant="v0", run_id=run_id,
    )
    graph = _RaisingGraph()
    cli_run._finalize_run_manifest(
        write=write, graph=graph, ticker="NVDA", trade_date="2026-11-20",
        asset_type="stock", portfolio=None,
        final_state={"final_rating": "Buy"},
        failure=None,
    )
    run_dir = tmp_path / "runs" / run_id
    manifest = read_manifest(run_dir / "manifest.json")
    assert manifest["evidence_snapshot"] is None
    sidecar = json.loads((run_dir / "evidence-mode.json").read_text(encoding="utf-8"))
    assert sidecar["snapshot_ref"] == {"snapshot_id": None, "artifact_key": None}


# --- 5. source_run_id forwarding (introspected) -----------------------------


def test_introspection_detects_source_run_id_support():
    def legacy(company_name, trade_date, asset_type="stock", portfolio=None):
        pass

    def supported(company_name, trade_date, asset_type="stock", portfolio=None, *, source_run_id=None):
        pass

    assert cli_run._callable_accepts_source_run_id(supported) is True
    assert cli_run._callable_accepts_source_run_id(legacy) is False


def test_source_run_id_forwarded_only_when_supported():
    seen = {}

    class _GraphOk:
        def create_run_state(self, company, trade_date, asset_type="stock", portfolio=None, *, source_run_id=None):
            seen["source_run_id"] = source_run_id
            return {}

    class _GraphLegacy:
        def create_run_state(self, company, trade_date, asset_type="stock", portfolio=None):
            seen["called"] = True
            return {}

    cli_run._create_run_state(_GraphOk(), "NVDA", "2026-11-20", "stock", None, "reserved-id")
    assert seen["source_run_id"] == "reserved-id"

    seen.clear()
    cli_run._create_run_state(_GraphLegacy(), "NVDA", "2026-11-20", "stock", None, "reserved-id")
    assert seen == {"called": True}

