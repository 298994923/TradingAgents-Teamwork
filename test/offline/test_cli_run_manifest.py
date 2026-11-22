"""Offline tests for wiring the run recorder into the CLI run path.

The CLI's ``run_analysis`` builds a graph and streams it, which cannot run offline;
the manifest-writing logic is therefore extracted into small helpers that these
tests exercise directly. The wiring itself (write before the checkpoint is cleared,
and again on failure) is checked with a stub graph.

Contract: one manifest per run at ``results_dir/runs/<run_id>/manifest.json``.
Owner fields not yet produced by other members use null/empty placeholders:
``stop_reason`` (C) -> None, ``prompt_hashes`` (B) -> {}, ``evidence_snapshot``
(A) -> None. A failing run still writes a manifest with ``failure`` set.
"""

from datetime import UTC, datetime

import pytest

import cli.run as cli_run
from tradingagents.run_recorder import read_manifest

FIXED_AT = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def _config(**overrides) -> dict:
    config = {
        "results_dir": "/tmp/results",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-6-luna",
        "deep_think_llm": "gpt-6-sol",
        "output_language": "English",
        "openai_api_key": "sk-should-not-persist",
    }
    config.update(overrides)
    return config


# --- config snapshot ---------------------------------------------------------


def test_secret_keys_never_reach_the_written_manifest(tmp_path):
    path = cli_run.write_run_manifest(
        config=_config(results_dir=str(tmp_path)),
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome="Buy",
        usage={"llm_calls": 1, "tool_calls": 0, "tokens_in": 1, "tokens_out": 0},
        duration_seconds=1.0,
        failure=None,
        variant="v2",
        repeat=1,
        at=FIXED_AT,
        version="0.7.1",
    )
    manifest = read_manifest(path)
    assert "openai_api_key" not in manifest["config_snapshot"]
    assert "sk-should-not-persist" not in path.read_text(encoding="utf-8")
    assert manifest["config_snapshot"]["llm_provider"] == "openai"


def test_config_snapshot_keeps_only_scalars():
    config = _config(nested={"a": 1}, some_list=[1, 2])
    snapshot = cli_run._manifest_config_snapshot(config)
    assert "nested" not in snapshot
    assert "some_list" not in snapshot


# --- write_run_manifest ------------------------------------------------------


def test_write_run_manifest_writes_under_runs_run_id(tmp_path):
    path = cli_run.write_run_manifest(
        config=_config(results_dir=str(tmp_path)),
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome="Buy",
        usage={"llm_calls": 3, "tool_calls": 1, "tokens_in": 10, "tokens_out": 5},
        duration_seconds=12.0,
        failure=None,
        variant="v2",
        repeat=1,
        at=FIXED_AT,
        version="0.7.1",
    )
    assert path == tmp_path / "runs" / path.parent.name / "manifest.json"
    assert path.parent.name == "v2-nvda-2026-11-20-r1-20261121t1200"
    manifest = read_manifest(path)
    assert manifest["ticker"] == "NVDA"
    assert manifest["outcome"] == "Buy"


def test_placeholders_for_owner_fields(tmp_path):
    path = cli_run.write_run_manifest(
        config=_config(results_dir=str(tmp_path)),
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome=None,
        usage={"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0},
        duration_seconds=None,
        failure=None,
        variant="v2",
        repeat=1,
        at=FIXED_AT,
        version="0.7.1",
    )
    manifest = read_manifest(path)
    assert manifest["stop_reason"] is None
    assert manifest["prompt_hashes"] == {}
    assert manifest["evidence_snapshot"] is None


def test_failed_run_records_failure(tmp_path):
    path = cli_run.write_run_manifest(
        config=_config(results_dir=str(tmp_path)),
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome=None,
        usage={"llm_calls": 1, "tool_calls": 0, "tokens_in": 5, "tokens_out": 0},
        duration_seconds=3.0,
        failure="boom",
        variant="v2",
        repeat=1,
        at=FIXED_AT,
        version="0.7.1",
    )
    assert read_manifest(path)["failure"] == "boom"


def test_unique_runs_do_not_collide(tmp_path):
    kwargs = {
        "config": _config(results_dir=str(tmp_path)),
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
        "outcome": "Buy",
        "usage": {"llm_calls": 1, "tool_calls": 0, "tokens_in": 1, "tokens_out": 0},
        "duration_seconds": 1.0,
        "failure": None,
        "variant": "v2",
        "version": "0.7.1",
    }
    first = cli_run.write_run_manifest(repeat=1, at=FIXED_AT, **kwargs)
    second = cli_run.write_run_manifest(
        repeat=2, at=datetime(2026, 11, 21, 12, 1, tzinfo=UTC), **kwargs
    )
    assert first != second
    assert first.exists() and second.exists()


def test_duration_measured_when_not_supplied(tmp_path):
    path = cli_run.write_run_manifest(
        config=_config(results_dir=str(tmp_path)),
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome="Buy",
        usage={"llm_calls": 1, "tool_calls": 0, "tokens_in": 1, "tokens_out": 0},
        duration_seconds=None,
        failure=None,
        variant="v2",
        repeat=1,
        at=FIXED_AT,
        version="0.7.1",
        started_at=FIXED_AT.timestamp() - 5.0,
        clock=lambda: FIXED_AT.timestamp(),
    )
    assert read_manifest(path)["duration_seconds"] == pytest.approx(5.0)


# --- collisions within one minute -------------------------------------------


def test_second_run_same_minute_does_not_crash(tmp_path):
    kwargs = {
        "config": _config(results_dir=str(tmp_path)),
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
        "outcome": "Buy",
        "usage": {"llm_calls": 1, "tool_calls": 0, "tokens_in": 1, "tokens_out": 0},
        "duration_seconds": 1.0,
        "failure": None,
        "variant": "v0",
        "repeat": 1,
        "at": FIXED_AT,
        "version": "0.7.1",
    }
    first = cli_run.write_run_manifest(**kwargs)
    # Same variant/repeat/minute -> identical build_run_id; must not raise.
    second = cli_run.write_run_manifest(**kwargs)
    third = cli_run.write_run_manifest(**kwargs)
    assert len({first, second, third}) == 3
    for path in (first, second, third):
        assert read_manifest(path)["run_id"] == path.parent.name


def test_collision_run_ids_stay_within_pattern(tmp_path):
    kwargs = {
        "config": _config(results_dir=str(tmp_path)),
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
        "outcome": "Buy",
        "usage": {"llm_calls": 1, "tool_calls": 0, "tokens_in": 1, "tokens_out": 0},
        "duration_seconds": 1.0,
        "failure": None,
        "variant": "v0",
        "repeat": 1,
        "at": FIXED_AT,
        "version": "0.7.1",
    }
    for _ in range(5):
        path = cli_run.write_run_manifest(**kwargs)
        read_manifest(path)  # the recorder rejects any invalid run_id


# --- wiring: started_at passed so real manifests record duration -------------


def test_make_manifest_writer_passes_started_at(monkeypatch):
    captured = {}

    def fake_write_run_manifest(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(cli_run, "write_run_manifest", fake_write_run_manifest)

    class _Stats:
        def get_stats(self):
            return {"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0}

    selections = {"ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock"}
    write = cli_run._make_manifest_writer(_config(), selections, _Stats(), started_at=123.0)
    write(failure=None, outcome="Buy")

    assert captured["started_at"] == 123.0
    assert captured.get("duration_seconds") is None  # let the helper measure it


# --- wiring: write before checkpoint clear, and on failure -------------------


class _StubGraph:
    def __init__(self, fail: bool):
        self.fail = fail
        self.cleared = False
        self.recorded = False

    def record_decision(self, *a, **k):
        self.recorded = True

    def clear_checkpoint_on_success(self, *a, **k):
        self.cleared = True


def test_manifest_written_before_checkpoint_cleared(tmp_path):
    events = []

    def write(**kw):
        events.append(("write", kw.get("failure")))
        return tmp_path / "manifest.json"

    graph = _StubGraph(fail=False)
    graph.clear_checkpoint_on_success = lambda *a, **k: events.append(("clear", None))

    cli_run._finalize_run_manifest(
        write=write,
        graph=graph,
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        portfolio=None,
        final_state={"final_trade_decision": "Buy"},
        failure=None,
    )
    # write must come before the checkpoint is cleared.
    assert events.index(("write", None)) < events.index(("clear", None))


def test_manifest_written_on_failure(tmp_path):
    written = {}

    def write(**kw):
        written.update(kw)
        return tmp_path / "manifest.json"

    graph = _StubGraph(fail=True)

    with pytest.raises(RuntimeError):
        cli_run._finalize_run_manifest(
            write=write,
            graph=graph,
            ticker="NVDA",
            trade_date="2026-11-20",
            asset_type="stock",
            portfolio=None,
            final_state=None,
            failure=RuntimeError("boom"),
        )
    assert written["failure"] == "boom"
    # A failed run must NOT clear the checkpoint (it is kept for resume).
    assert graph.cleared is False
