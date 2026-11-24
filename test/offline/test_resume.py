"""Offline tests for E3: attempts.jsonl, checkpoint.json, resolve_run (E3).

Contract (docs/handoffs/E-interfaces-v1.md §E3):

- ``<results_dir>/runs/<run_id>/attempts.jsonl`` — one JSON line per attempt,
  ``{schema_version, run_id, at, stage, status, reason_code, detail}``. A
  recoverable failure writes only here; the manifest slot stays free.
- ``<results_dir>/runs/<run_id>/checkpoint.json`` — the locator:
  ``{schema_version, run_id, ticker, trade_date, asset_type, created_at, status,
  checkpoint:{backend,db_relpath,thread_id,step},
  evidence_snapshot:{snapshot_id,artifact_key,store,source_run_id,captured_at}}``.
- ``resolve_run(run_id, config) -> ResumeRef`` with typed ``ResumeError.code``.

Three-step semantics: first failure appends an attempt (manifest unclaimed) → resuming
the same id succeeds, writes the one manifest, and clears the checkpoint → a further
request returns ``already_recorded`` (identity+terminal match only).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingagents.resume import (
    ResumeError,
    ResumeRef,
    append_attempt,
    checkpoint_path,
    read_attempts,
    resolve_run,
    write_checkpoint,
    write_manifest_then_clear,
)

RUN_ID = "v0-nvda-2026-11-20-r1-20261122t1200"
AT = "2026-11-22T12:00:00+00:00"


def _config(tmp_path) -> dict:
    return {
        "results_dir": str(tmp_path),
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
    }


def _checkpoint_kwargs(**overrides):
    kwargs = {
        "backend": "sqlite",
        "db_relpath": "checkpoints.db",
        "thread_id": "v0-nvda-2026-11-20-r1-20261122t1200",
        "step": 7,
    }
    kwargs.update(overrides)
    return kwargs


def _snapshot_kwargs(**overrides):
    kwargs = {
        "snapshot_id": "snap-abc",
        "artifact_key": "v1/deadbeef.json",
        "store": "evidence",
        "source_run_id": RUN_ID,
        "captured_at": AT,
    }
    kwargs.update(overrides)
    return kwargs


def _write_checkpoint(tmp_path, *, run_id=RUN_ID, ticker="NVDA", trade_date="2026-11-20",
                      asset_type="stock", checkpoint=None, snapshot=None):
    return write_checkpoint(
        _config(tmp_path),
        run_id,
        ticker=ticker,
        trade_date=trade_date,
        asset_type=asset_type,
        created_at=AT,
        status="incomplete",
        checkpoint=checkpoint if checkpoint is not None else _checkpoint_kwargs(),
        evidence_snapshot=snapshot if snapshot is not None else _snapshot_kwargs(),
    )


# --- attempts.jsonl ----------------------------------------------------------


def test_first_failure_appends_attempt_and_manifest_slot_free(tmp_path):
    append_attempt(
        _config(tmp_path),
        RUN_ID,
        at=AT,
        stage="graph",
        status="failed",
        reason_code="checkpoint_unreadable",
        detail="boom",
    )
    attempts_file = Path(tmp_path) / "runs" / RUN_ID / "attempts.jsonl"
    assert attempts_file.exists()
    line = json.loads(attempts_file.read_text(encoding="utf-8").splitlines()[0])
    assert line == {
        "schema_version": 1,
        "run_id": RUN_ID,
        "at": AT,
        "stage": "graph",
        "status": "failed",
        "reason_code": "checkpoint_unreadable",
        "detail": "boom",
    }
    assert not (Path(tmp_path) / "runs" / RUN_ID / "manifest.json").exists()


def test_attempts_append_is_additive(tmp_path):
    for stage in ("first", "second"):
        append_attempt(
            _config(tmp_path), RUN_ID, at=AT, stage=stage, status="failed", reason_code="x"
        )
    lines = read_attempts(_config(tmp_path), RUN_ID)
    assert [line["stage"] for line in lines] == ["first", "second"]


def test_detail_defaults_to_none(tmp_path):
    append_attempt(_config(tmp_path), RUN_ID, at=AT, stage="s", status="failed", reason_code="r")
    assert read_attempts(_config(tmp_path), RUN_ID)[0]["detail"] is None


# --- checkpoint.json read/write ---------------------------------------------


def test_write_checkpoint_roundtrip(tmp_path):
    path = _write_checkpoint(tmp_path)
    assert path == checkpoint_path(_config(tmp_path), RUN_ID)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["run_id"] == RUN_ID
    assert data["checkpoint"]["thread_id"] == RUN_ID
    assert data["evidence_snapshot"]["snapshot_id"] == "snap-abc"


# --- resolve_run -------------------------------------------------------------


def test_resolve_run_returns_resumeref(tmp_path):
    _write_checkpoint(tmp_path)
    ref = resolve_run(RUN_ID, _config(tmp_path))
    assert isinstance(ref, ResumeRef)
    assert ref.thread_id == RUN_ID
    assert ref.step == 7
    assert ref.snapshot_id == "snap-abc"
    assert ref.artifact_key == "v1/deadbeef.json"
    assert ref.source_run_id == RUN_ID


def test_resolve_run_locator_missing(tmp_path):
    with pytest.raises(ResumeError) as exc:
        resolve_run(RUN_ID, _config(tmp_path))
    assert exc.value.code == "locator_missing"


def test_snapshot_published_but_locator_missing(tmp_path):
    # The snapshot artifact exists on disk, but checkpoint.json (the locator) does not.
    snap = Path(tmp_path) / "evidence" / "v1" / "deadbeef.json"
    snap.parent.mkdir(parents=True)
    snap.write_text("{}", encoding="utf-8")
    with pytest.raises(ResumeError) as exc:
        resolve_run(RUN_ID, _config(tmp_path))
    assert exc.value.code == "locator_missing"
    assert snap.exists()


def test_resolve_run_signature_mismatch(tmp_path):
    _write_checkpoint(tmp_path, ticker="AMD")
    with pytest.raises(ResumeError) as exc:
        resolve_run(RUN_ID, _config(tmp_path))  # config expects NVDA
    assert exc.value.code == "checkpoint_signature_mismatch"


def test_resolve_run_corrupt_checkpoint(tmp_path):
    path = checkpoint_path(_config(tmp_path), RUN_ID)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ResumeError) as exc:
        resolve_run(RUN_ID, _config(tmp_path))
    assert exc.value.code == "checkpoint_corrupt"


def test_resolve_run_snapshot_id_mismatch(tmp_path):
    _write_checkpoint(tmp_path, snapshot=_snapshot_kwargs(snapshot_id="different"))
    # A caller that pins the expected snapshot id must get a mismatch code.
    with pytest.raises(ResumeError) as exc:
        resolve_run(RUN_ID, _config(tmp_path), expected_snapshot_id="snap-abc")
    assert exc.value.code == "snapshot_id_mismatch"


def _valid_manifest_dict():
    """A complete, valid v1 manifest with ``failure`` null (as run_recorder writes)."""
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "created_at": AT,
        "version": "0.7.1",
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
        "outcome": "Buy",
        "config_snapshot": {},
        "prompt_hashes": {},
        "evidence_snapshot": None,
        "usage": {"llm_calls": 0, "tool_calls": 0, "tokens_in": None, "tokens_out": None},
        "duration_seconds": 1.0,
        "failure": None,
        "stop_reason": None,
    }


def test_resolve_run_already_recorded(tmp_path):
    _write_checkpoint(tmp_path)
    # A complete, valid manifest with failure null for this run already exists.
    manifest = checkpoint_path(_config(tmp_path), RUN_ID).parent / "manifest.json"
    manifest.write_text(json.dumps(_valid_manifest_dict()), encoding="utf-8")
    with pytest.raises(ResumeError) as exc:
        resolve_run(RUN_ID, _config(tmp_path))
    assert exc.value.code == "already_recorded"


def test_truncated_manifest_does_not_count_as_recorded(tmp_path):
    _write_checkpoint(tmp_path)
    manifest = checkpoint_path(_config(tmp_path), RUN_ID).parent / "manifest.json"
    manifest.write_text('{"schema_version": 1, "run_id": ', encoding="utf-8")  # truncated
    # A truncated manifest must not block the retry: resolve falls through to the
    # checkpoint and returns a usable ref.
    ref = resolve_run(RUN_ID, _config(tmp_path))
    assert isinstance(ref, ResumeRef)


def test_failed_manifest_does_not_count_as_recorded(tmp_path):
    _write_checkpoint(tmp_path)
    manifest = checkpoint_path(_config(tmp_path), RUN_ID).parent / "manifest.json"
    payload = _valid_manifest_dict()
    payload["failure"] = "boom"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    # A manifest that recorded a failure is not a completed run.
    ref = resolve_run(RUN_ID, _config(tmp_path))
    assert isinstance(ref, ResumeRef)


def test_incomplete_manifest_does_not_count_as_recorded(tmp_path):
    _write_checkpoint(tmp_path)
    manifest = checkpoint_path(_config(tmp_path), RUN_ID).parent / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "run_id": RUN_ID}), encoding="utf-8")
    # Missing required fields / no ``failure`` key: not a valid completion.
    ref = resolve_run(RUN_ID, _config(tmp_path))
    assert isinstance(ref, ResumeRef)


def test_wrong_schema_manifest_does_not_count_as_recorded(tmp_path):
    _write_checkpoint(tmp_path)
    manifest = checkpoint_path(_config(tmp_path), RUN_ID).parent / "manifest.json"
    payload = _valid_manifest_dict()
    payload["schema_version"] = 999
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    ref = resolve_run(RUN_ID, _config(tmp_path))
    assert isinstance(ref, ResumeRef)


# --- three-step: resume success clears checkpoint ----------------------------


def test_resume_success_writes_manifest_and_clears_checkpoint(tmp_path):
    config = _config(tmp_path)

    def write_manifest():
        (checkpoint_path(config, RUN_ID).parent / "manifest.json").write_text(
            json.dumps({"schema_version": 1, "run_id": RUN_ID}), encoding="utf-8"
        )

    write_manifest_then_clear(config, RUN_ID, write_manifest=write_manifest)
    assert (checkpoint_path(config, RUN_ID).parent / "manifest.json").exists()
    assert not checkpoint_path(config, RUN_ID).exists()


def test_manifest_write_failure_keeps_checkpoint(tmp_path):
    config = _config(tmp_path)
    _write_checkpoint(tmp_path)

    def failing_write():
        raise OSError("disk full")

    with pytest.raises(OSError):
        write_manifest_then_clear(config, RUN_ID, write_manifest=failing_write)
    # Checkpoint kept so a retry can resume; manifest never appeared.
    assert checkpoint_path(config, RUN_ID).exists()
    assert not (checkpoint_path(config, RUN_ID).parent / "manifest.json").exists()
