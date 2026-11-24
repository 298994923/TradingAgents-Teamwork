"""Run resume / attempts / checkpoint locator (E3).

Contract: ``docs/handoffs/E-interfaces-v1.md`` §E3. The pieces here are E-owned and
depend on no other member for their format; a real end-to-end resume needs C's
``checkpoint_thread_id(..., run_key=run_id)`` and state binding, so ``thread_id`` is
injected by the caller rather than computed here.

Layout under ``<results_dir>/runs/<run_id>/``:

- ``attempts.jsonl`` — one JSON line per attempt (recoverable failures live only here;
  the manifest slot stays free).
- ``checkpoint.json`` — the locator: run identity, checkpoint location, and the
  evidence snapshot pointer.
- ``manifest.json`` — written once on terminal success (by ``run_recorder``); its
  presence is what makes a later ``resolve_run`` return ``already_recorded``.

Three-step semantics: a first failure appends an attempt (no manifest) → resuming the
same ``run_id`` succeeds, writes the one manifest, and clears the checkpoint → a
further request returns ``already_recorded``.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

# Typed resume failure codes (docs/handoffs/E-interfaces-v1.md §E3).
RESUME_ERROR_CODES = (
    "locator_missing",
    "locator_invalid",
    "checkpoint_not_found",
    "checkpoint_unreadable",
    "checkpoint_corrupt",
    "checkpoint_signature_mismatch",
    "snapshot_missing",
    "snapshot_unreadable",
    "snapshot_corrupt",
    "snapshot_id_mismatch",
    "already_recorded",
)


class ResumeError(Exception):
    """A resume could not proceed; ``code`` names the typed reason."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        if code not in RESUME_ERROR_CODES:
            raise ValueError(f"unknown resume error code {code!r}")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class ResumeRef:
    """What a resumed run needs: where its checkpoint and evidence snapshot are."""

    db: str
    thread_id: str
    step: int | None
    snapshot_id: str | None
    artifact_key: str | None
    source_run_id: str | None
    captured_at: str | None


def run_dir(config: dict, run_id: str) -> Path:
    return Path(config["results_dir"]) / "runs" / run_id


def attempts_path(config: dict, run_id: str) -> Path:
    return run_dir(config, run_id) / "attempts.jsonl"


def checkpoint_path(config: dict, run_id: str) -> Path:
    return run_dir(config, run_id) / "checkpoint.json"


def manifest_path(config: dict, run_id: str) -> Path:
    return run_dir(config, run_id) / "manifest.json"


# --- attempts ----------------------------------------------------------------


def append_attempt(
    config: dict,
    run_id: str,
    *,
    at: str,
    stage: str,
    status: str,
    reason_code: str,
    detail: str | None = None,
) -> Path:
    """Append one attempt line; the manifest slot is not touched."""
    path = attempts_path(config, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "at": at,
        "stage": stage,
        "status": status,
        "reason_code": reason_code,
        "detail": detail,
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return path


def read_attempts(config: dict, run_id: str) -> list[dict]:
    path = attempts_path(config, run_id)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


# --- checkpoint --------------------------------------------------------------


def write_checkpoint(
    config: dict,
    run_id: str,
    *,
    ticker: str,
    trade_date: str,
    asset_type: str,
    created_at: str,
    status: str,
    checkpoint: dict,
    evidence_snapshot: dict,
) -> Path:
    """Write ``checkpoint.json`` atomically (temp file + ``os.replace``)."""
    path = checkpoint_path(config, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    locator = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "ticker": ticker,
        "trade_date": trade_date,
        "asset_type": asset_type,
        "created_at": created_at,
        "status": status,
        "checkpoint": {
            "backend": checkpoint.get("backend"),
            "db_relpath": checkpoint.get("db_relpath"),
            "thread_id": checkpoint.get("thread_id"),
            "step": checkpoint.get("step"),
        },
        "evidence_snapshot": {
            "snapshot_id": evidence_snapshot.get("snapshot_id"),
            "artifact_key": evidence_snapshot.get("artifact_key"),
            "store": evidence_snapshot.get("store"),
            "source_run_id": evidence_snapshot.get("source_run_id"),
            "captured_at": evidence_snapshot.get("captured_at"),
        },
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(locator, sort_keys=True, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


def _read_checkpoint_file(path: Path) -> dict:
    if not path.exists():
        raise ResumeError("locator_missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ResumeError("checkpoint_unreadable", str(exc)) from exc
    except ValueError as exc:
        raise ResumeError("checkpoint_corrupt", str(exc)) from exc
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ResumeError("locator_invalid")
    for key in ("run_id", "ticker", "trade_date", "asset_type", "checkpoint", "evidence_snapshot"):
        if key not in data:
            raise ResumeError("locator_invalid", f"missing {key!r}")
    return data


def resolve_run(
    run_id: str,
    config: dict,
    *,
    expected_ticker: str | None = None,
    expected_trade_date: str | None = None,
    expected_asset_type: str | None = None,
    expected_snapshot_id: str | None = None,
    backend_root: str | Path | None = None,
    verify_snapshot: bool = False,
) -> ResumeRef:
    """Resolve a run's checkpoint and evidence snapshot, or raise ``ResumeError``.

    ``already_recorded`` is checked first: a terminal manifest for this ``run_id``
    means the run already completed and must not run again. Identity fields inside
    the locator must match the run_id and any caller-supplied expectations, else
    ``checkpoint_signature_mismatch``. ``thread_id`` is injected in the locator, not
    computed here. The snapshot artifact is verified only when ``verify_snapshot`` is
    set (a caller about to resume wants proof the snapshot is still readable).
    """
    if manifest_path(config, run_id).exists():
        raise ResumeError("already_recorded")

    data = _read_checkpoint_file(checkpoint_path(config, run_id))

    if data.get("run_id") != run_id:
        raise ResumeError("checkpoint_signature_mismatch", "run_id")

    # Identity expectations default to the config's resolved instrument, so a
    # locator for a different ticker/date/asset is rejected out of the box.
    checks = (
        ("ticker", expected_ticker if expected_ticker is not None else config.get("ticker")),
        (
            "trade_date",
            expected_trade_date if expected_trade_date is not None else config.get("trade_date"),
        ),
        (
            "asset_type",
            expected_asset_type if expected_asset_type is not None else config.get("asset_type"),
        ),
    )
    for field, expected in checks:
        if expected is not None and data.get(field) != expected:
            raise ResumeError("checkpoint_signature_mismatch", field)

    checkpoint = data.get("checkpoint") or {}
    snapshot = data.get("evidence_snapshot") or {}
    thread_id = checkpoint.get("thread_id")
    if not thread_id:
        raise ResumeError("locator_invalid", "checkpoint.thread_id")

    snapshot_id = snapshot.get("snapshot_id")
    if expected_snapshot_id is not None and snapshot_id != expected_snapshot_id:
        raise ResumeError("snapshot_id_mismatch", snapshot_id)

    artifact_key = snapshot.get("artifact_key")
    store = snapshot.get("store")
    if verify_snapshot and snapshot_id is not None and artifact_key is not None:
        _verify_snapshot_artifact(config, store, artifact_key, backend_root)

    db = _resolve_db_path(config, data, checkpoint)

    return ResumeRef(
        db=str(db),
        thread_id=str(thread_id),
        step=checkpoint.get("step"),
        snapshot_id=snapshot_id,
        artifact_key=artifact_key,
        source_run_id=snapshot.get("source_run_id"),
        captured_at=snapshot.get("captured_at"),
    )


def _resolve_db_path(config: dict, data: dict, checkpoint: dict) -> Path:
    db_relpath = checkpoint.get("db_relpath")
    if not db_relpath:
        # Default to the run directory; the caller may still inject the real path.
        return run_dir(config, data.get("run_id")) / "checkpoints.db"
    db_path = Path(db_relpath)
    if db_path.is_absolute():
        return db_path
    return run_dir(config, data.get("run_id")) / db_path


def _verify_snapshot_artifact(
    config: dict, store: str | None, artifact_key: str, backend_root: str | Path | None
) -> None:
    root = Path(backend_root) if backend_root is not None else Path(config["results_dir"])
    base = root / store if store else root
    artifact = base / artifact_key
    if not artifact.exists():
        raise ResumeError("snapshot_missing", str(artifact))
    try:
        json.loads(artifact.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ResumeError("snapshot_unreadable", str(exc)) from exc
    except ValueError as exc:
        raise ResumeError("snapshot_corrupt", str(exc)) from exc


# --- three-step success path -------------------------------------------------


def write_manifest_then_clear(
    config: dict, run_id: str, *, write_manifest: Callable[[], Any]
) -> Path:
    """Write the one manifest, then clear the checkpoint; keep it if the write fails.

    ``write_manifest`` is injected so the manifest shape stays owned by
    ``run_recorder``. If it raises, the checkpoint is left in place for a retry and
    the error propagates; only after a successful write is the checkpoint removed.
    """
    run_dir(config, run_id).mkdir(parents=True, exist_ok=True)
    result = write_manifest()
    cp = checkpoint_path(config, run_id)
    if cp.exists():
        cp.unlink()
    return result
