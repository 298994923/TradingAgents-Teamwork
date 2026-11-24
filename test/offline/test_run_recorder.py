"""Offline tests for the RunEvent recorder (docs/contracts/run-event.md).

Written test-first before the implementation (commit ``abd040b``); the module landed
in ``a6a4a6b``. No custom pytest marker is used; the default
``-m "not integration"`` runs these tests.
"""

import json
from datetime import UTC, datetime

import pytest

from tradingagents.run_recorder import (
    SCHEMA_VERSION,
    RunEvent,
    build_run_id,
    read_manifest,
    write_manifest,
)

REQUIRED_FIELDS = (
    "schema_version",
    "run_id",
    "created_at",
    "version",
    "ticker",
    "trade_date",
    "asset_type",
    "outcome",
    "config_snapshot",
    "prompt_hashes",
    "evidence_snapshot",
    "usage",
    "duration_seconds",
    "failure",
    "stop_reason",
)


def _event_kwargs(**overrides) -> dict:
    fields = {
        "run_id": "run-abc-001",
        "created_at": "2026-11-21T12:00:00+00:00",
        "version": "0.1.0",
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
        "outcome": "Buy",
        "config_snapshot": {"llm_provider": "openai", "deep_think_llm": "gpt-5"},
        "prompt_hashes": {"market": "sha256:aaa"},
        "evidence_snapshot": {"snapshot_id": "snap-1"},
        "usage": {"llm_calls": 12, "tool_calls": 7, "tokens_in": 1000, "tokens_out": 500},
        "duration_seconds": 42.5,
        "failure": None,
        "stop_reason": "completed",
    }
    fields.update(overrides)
    return fields


def _make_event(**overrides) -> RunEvent:
    return RunEvent(**_event_kwargs(**overrides))


def _write_to(tmp_path, event, name="manifest.json"):
    path = tmp_path / name
    write_manifest(event, path)
    return path


def test_round_trip_preserves_all_fields(tmp_path):
    event = _make_event()
    path = _write_to(tmp_path, event)

    manifest = read_manifest(path)

    assert set(manifest) == set(REQUIRED_FIELDS)
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["run_id"] == "run-abc-001"
    assert manifest["created_at"] == "2026-11-21T12:00:00+00:00"
    assert manifest["version"] == "0.1.0"
    assert manifest["ticker"] == "NVDA"
    assert manifest["trade_date"] == "2026-11-20"
    assert manifest["asset_type"] == "stock"
    assert manifest["outcome"] == "Buy"
    assert manifest["config_snapshot"] == {"llm_provider": "openai", "deep_think_llm": "gpt-5"}
    assert manifest["prompt_hashes"] == {"market": "sha256:aaa"}
    assert manifest["evidence_snapshot"] == {"snapshot_id": "snap-1"}
    assert manifest["usage"] == {"llm_calls": 12, "tool_calls": 7, "tokens_in": 1000, "tokens_out": 500}
    assert manifest["duration_seconds"] == 42.5
    assert manifest["failure"] is None
    assert manifest["stop_reason"] == "completed"


def test_identical_inputs_produce_byte_identical_output(tmp_path):
    path_a = _write_to(tmp_path, _make_event(), "a.json")
    path_b = _write_to(tmp_path, _make_event(), "b.json")

    assert path_a.read_bytes() == path_b.read_bytes()


def test_missing_required_field_is_rejected():
    fields = _event_kwargs()
    del fields["version"]
    with pytest.raises(TypeError):
        RunEvent(**fields)


def test_empty_required_field_is_rejected(tmp_path):
    event = _make_event(ticker="")

    with pytest.raises(ValueError):
        write_manifest(event, tmp_path / "bad.json")


def test_unsupported_schema_version_is_rejected(tmp_path):
    event = _make_event(schema_version=999)

    with pytest.raises(ValueError):
        write_manifest(event, tmp_path / "bad.json")


def test_unsupported_schema_version_on_read_is_rejected(tmp_path):
    path = tmp_path / "bad.json"
    payload = {"schema_version": 999}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError):
        read_manifest(path)


def test_read_missing_required_key_is_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")

    with pytest.raises(ValueError):
        read_manifest(path)


def test_secret_pattern_config_key_excluded_from_snapshot(tmp_path):
    event = _make_event(
        config_snapshot={
            "llm_provider": "openai",
            "openai_api_key": "sk-should-not-be-written",
            "backend_url": "https://user:pass@example.test",
        }
    )
    path = _write_to(tmp_path, event)

    manifest = read_manifest(path)
    assert manifest["config_snapshot"] == {"llm_provider": "openai"}
    assert "sk-should-not-be-written" not in path.read_text(encoding="utf-8")


def test_invalid_run_id_charset_is_rejected(tmp_path):
    for bad_id in ("../etc/passwd", "V2-NVDA"):
        event = _make_event(run_id=bad_id)
        with pytest.raises(ValueError):
            write_manifest(event, tmp_path / "bad.json")


def test_build_run_id_format():
    at = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
    assert build_run_id("v2", "nvda", "2026-11-20", 1, at) == "v2-nvda-2026-11-20-r1-20261121t1200"


def test_build_run_id_rejects_repeat_below_one():
    at = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
    with pytest.raises(ValueError):
        build_run_id("v2", "nvda", "2026-11-20", 0, at)


def test_existing_manifest_is_not_overwritten(tmp_path):
    path = _write_to(tmp_path, _make_event())
    with pytest.raises(FileExistsError):
        write_manifest(_make_event(), path)


def test_interrupted_write_leaves_no_half_written_final_file(tmp_path, monkeypatch):
    # If the write is interrupted before the atomic publish, nothing must appear at
    # the final path: the bytes go to a temp file in the same directory first.
    path = tmp_path / "manifest.json"

    import tradingagents.run_recorder as rec

    def explode(src, dst):
        raise OSError("simulated crash before publish")

    monkeypatch.setattr(rec.os, "link", explode)
    with pytest.raises(OSError):
        write_manifest(_make_event(), path)

    assert not path.exists(), "no half-written file may reach the final path"
    # The temp file was cleaned up on the failure path too.
    assert list(tmp_path.iterdir()) == []


def test_successful_write_leaves_no_temp_file(tmp_path):
    path = _write_to(tmp_path, _make_event())
    leftovers = [p for p in tmp_path.iterdir() if p != path]
    assert leftovers == []
    assert read_manifest(path)["run_id"] == "run-abc-001"


def test_atomic_write_still_refuses_overwrite(tmp_path):
    path = _write_to(tmp_path, _make_event())
    with pytest.raises(FileExistsError):
        write_manifest(_make_event(), path)
    # The existing manifest is untouched.
    assert read_manifest(path)["run_id"] == "run-abc-001"
