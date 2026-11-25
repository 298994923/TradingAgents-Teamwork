"""Draft test oracle for observed Evidence outputs; never produces runtime state."""
import json
from pathlib import Path

from tradingagents.evidence import load_snapshot

FIELDS = {"snapshot_id", "artifact_key", "store", "source_run_id", "captured_at"}


def assert_fresh_capture(*, final_state, manifest_path, artifact_root,
                         expected_run_id, expected_capture_time,
                         expected_reports, expected_context):
    """A-EV-01/02/05/08: check actual observations against independent inputs.

    Future graph/CLI tests must pass their real outputs to this oracle. Passing a
    hand-built state only checks the oracle/sample contract, not graph integration.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    reference = final_state.get("evidence_snapshot")
    assert isinstance(reference, dict), "successful capture has no state reference"
    assert set(reference) == FIELDS, "reference must have exactly five agreed fields"
    assert manifest["evidence_snapshot"] == reference, "state/manifest reference mismatch"
    assert manifest["run_id"] == expected_run_id, "manifest did not reuse the reserved ID"
    assert reference["source_run_id"] == expected_run_id, "fresh source ID mismatch"
    assert reference["captured_at"] == expected_capture_time, "capture time was replaced"
    assert reference["store"] == "local-fs", "unexpected store"

    identity = reference["snapshot_id"]
    assert isinstance(identity, str) and identity.startswith("sha256:")
    digest = identity[7:]
    assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
    key = reference["artifact_key"]
    assert key == "v1/" + digest + ".json", "artifact key does not match identity"
    root = Path(artifact_root).resolve()
    artifact = (root / key).resolve()
    assert artifact.is_relative_to(root), "artifact escapes configured root"
    loaded = load_snapshot(artifact, expected_snapshot_id=identity)
    snapshot = loaded.snapshot
    assert snapshot.source_run_id == expected_run_id
    assert snapshot.captured_at == expected_capture_time
    assert snapshot.to_dict()["context"] == expected_context
    assert set(snapshot.reports) == set(expected_reports), "selected report set changed"
    for analyst, content in expected_reports.items():
        assert snapshot.reports[analyst].content == content, "report content changed"
    return snapshot


def assert_no_published_reference(*, final_state, manifest_path):
    """A-EV-05/06: use only for an explicitly disabled or failed capture case.

    Absence alone does not prove why capture was unavailable. Future integration
    tests must also assert the actual failure or deliberate disable decision.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    assert final_state.get("evidence_snapshot") is None
    assert manifest["evidence_snapshot"] is None
