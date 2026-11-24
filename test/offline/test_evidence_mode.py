"""Offline tests for E4: evidence-mode.json sidecar + compare control.

E4 (docs/handoffs/E-interfaces-v1.md §E4) records a per-run sidecar next to the
manifest. The comparator treats ``evidence_mode`` as a control: strict and
report_reference runs are never compared together. E records facts only; the
authoritative action/mode approval belong to D/C.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import compare_runs  # noqa: E402
from compare_runs import IncomparableRunsError  # noqa: E402

import cli.run as cli_run  # noqa: E402

FIXED_AT = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)

CONFIG = {
    "results_dir": "/tmp/results",
    "llm_provider": "openai",
    "quick_think_llm": "gpt-6-luna",
    "deep_think_llm": "gpt-6-sol",
    "output_language": "English",
}

SIDECAR_KEYS = {
    "schema_version",
    "run_id",
    "evidence_mode",
    "scenario",
    "policy_version",
    "unknown_time_fields",
    "limitations",
    "authoritative_action",
    "authoritative_reason",
    "decided_by",
    "snapshot_ref",
}


def _manifest(run_id, **overrides):
    base = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": "2026-11-22T12:00:00+00:00",
        "version": "0.7.1",
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
        "outcome": "Buy",
        "config_snapshot": {k: v for k, v in CONFIG.items() if k != "results_dir"},
        "prompt_hashes": {"market": "sha256:aaa"},
        "evidence_snapshot": None,
        "usage": {"llm_calls": 1, "tool_calls": 0, "tokens_in": 10, "tokens_out": 5},
        "duration_seconds": 1.0,
        "failure": None,
        "stop_reason": None,
    }
    base.update(overrides)
    return base


# --- sidecar write -----------------------------------------------------------


def _write_run(tmp_path, evidence_mode, **kwargs):
    return cli_run.write_run_manifest(
        config={"results_dir": str(tmp_path), **{k: v for k, v in CONFIG.items() if k != "results_dir"}},
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome="Buy",
        usage={"llm_calls": 1, "tool_calls": 0, "tokens_in": 10, "tokens_out": 5},
        duration_seconds=1.0,
        failure=None,
        variant="v0",
        repeat=1,
        at=FIXED_AT,
        version="0.7.1",
        evidence_mode=evidence_mode,
        **kwargs,
    )


def test_sidecar_written_with_all_fields(tmp_path):
    manifest_path = _write_run(tmp_path, "report_reference")
    sidecar = manifest_path.parent / "evidence-mode.json"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert set(data) == SIDECAR_KEYS
    assert data["schema_version"] == 1
    assert data["evidence_mode"] == "report_reference"
    assert data["run_id"] == manifest_path.parent.name
    assert data["unknown_time_fields"] == []
    assert data["limitations"] == []
    assert data["snapshot_ref"] == {"snapshot_id": None, "artifact_key": None}


def test_sidecar_strict_mode(tmp_path):
    manifest_path = _write_run(tmp_path, "strict")
    data = json.loads((manifest_path.parent / "evidence-mode.json").read_text())
    assert data["evidence_mode"] == "strict"


def test_invalid_evidence_mode_rejected(tmp_path):
    with pytest.raises(ValueError):
        _write_run(tmp_path, "loose")


def test_default_evidence_mode_is_strict(tmp_path):
    path = cli_run.write_run_manifest(
        config={"results_dir": str(tmp_path), "llm_provider": "openai"},
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome="Buy",
        usage={"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0},
        duration_seconds=1.0,
        failure=None,
        variant="v0",
        repeat=1,
        at=FIXED_AT,
        version="0.7.1",
    )
    data = json.loads((path.parent / "evidence-mode.json").read_text())
    assert data["evidence_mode"] == "strict"


# --- compare: evidence_mode is a control -------------------------------------


def test_compare_refuses_strict_vs_report_reference():
    a = _manifest("v0-nvda-2026-11-20-r1-20261122t1200")
    b = _manifest("v2-nvda-2026-11-20-r1-20261122t1200")
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifests([a, b], evidence_modes=["strict", "report_reference"])
    assert "evidence_mode" in str(exc.value)


def test_compare_allows_same_mode():
    a = _manifest("v0-nvda-2026-11-20-r1-20261122t1200")
    b = _manifest("v2-nvda-2026-11-20-r1-20261122t1200")
    comparison = compare_runs.compare_manifests([a, b], evidence_modes=["strict", "strict"])
    assert comparison.guard.get("evidence_mode") == "strict"


def test_compare_missing_sidecar_compares_with_missing():
    a = _manifest("v0-nvda-2026-11-20-r1-20261122t1200")
    b = _manifest("v2-nvda-2026-11-20-r1-20261122t1200")
    comparison = compare_runs.compare_manifests([a, b])  # no modes -> both None
    assert len(comparison.variants) == 2


def test_compare_missing_sidecar_vs_strict_refused():
    a = _manifest("v0-nvda-2026-11-20-r1-20261122t1200")
    b = _manifest("v2-nvda-2026-11-20-r1-20261122t1200")
    with pytest.raises(IncomparableRunsError):
        compare_runs.compare_manifests([a, b], evidence_modes=[None, "strict"])


def _write_manifest_and_sidecar(tmp_path, run_id, evidence_mode):
    """Write a real manifest + sidecar under tmp_path/runs/<run_id>/."""
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    manifest = _manifest(run_id)
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    sidecar = {
        "schema_version": 1,
        "run_id": run_id,
        "evidence_mode": evidence_mode,
        "scenario": None,
        "policy_version": None,
        "unknown_time_fields": [],
        "limitations": [],
        "authoritative_action": None,
        "authoritative_reason": None,
        "decided_by": None,
        "snapshot_ref": {"snapshot_id": None, "artifact_key": None},
    }
    (run_dir / "evidence-mode.json").write_text(json.dumps(sidecar), encoding="utf-8")
    return run_dir / "manifest.json"


def test_file_level_reads_sidecars_and_refuses_mix(tmp_path):
    strict = _write_manifest_and_sidecar(tmp_path, "v0-nvda-2026-11-20-r1-20261122t1200", "strict")
    other = _write_manifest_and_sidecar(
        tmp_path, "v2-nvda-2026-11-20-r1-20261122t1200", "report_reference"
    )
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifest_files([strict, other])
    assert "evidence_mode" in str(exc.value)


def test_file_level_same_mode_passes(tmp_path):
    a = _write_manifest_and_sidecar(tmp_path, "v0-nvda-2026-11-20-r1-20261122t1200", "strict")
    b = _write_manifest_and_sidecar(tmp_path, "v2-nvda-2026-11-20-r1-20261122t1200", "strict")
    comparison = compare_runs.compare_manifest_files([a, b])
    assert len(comparison.variants) == 2


def test_file_level_no_sidecar_is_none(tmp_path):
    a = _write_manifest_and_sidecar(tmp_path, "v0-nvda-2026-11-20-r1-20261122t1200", "strict")
    b_dir = tmp_path / "runs" / "v2-nvda-2026-11-20-r1-20261122t1200"
    b_dir.mkdir(parents=True)
    (b_dir / "manifest.json").write_text(
        json.dumps(_manifest("v2-nvda-2026-11-20-r1-20261122t1200")), encoding="utf-8"
    )
    # strict vs no-sidecar (None) -> refused
    with pytest.raises(IncomparableRunsError):
        compare_runs.compare_manifest_files([a, b_dir / "manifest.json"])


def test_evidence_mode_reported_in_rows(tmp_path):
    path = _write_manifest_and_sidecar(tmp_path, "v0-nvda-2026-11-20-r1-20261122t1200", "strict")
    comparison = compare_runs.compare_manifests(
        [json.loads(path.read_text())],
        evidence_modes=["strict"],
    )
    assert comparison.variants[0]["evidence_mode"] == "strict"
