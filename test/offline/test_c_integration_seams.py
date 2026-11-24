"""Offline tests for the C/E integration seams that need no new C code.

C's replies (docs/handoffs/C-to-E-variant-and-stop-reason-response.md and
C-to-E-evidence-checkpoint-contract-alignment (2).md) propose a top-level
``stop_reason`` on the final state and a ``workflow_variant`` config key, neither of
which is wired into the graph yet. These tests pin the four seams we can land now:

1. ``stop_reason`` is read from ``final_state`` with a ``None`` fallback.
2. ``v1``/``v2`` are rejected before any model call until ``workflow_variant`` exists.
3. ``compare_runs`` refuses manifests whose ``prompt_hashes`` is empty.
4. Missing usage stays ``null`` (per run and in averages), never ``0``.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import compare_runs  # noqa: E402
from compare_runs import IncomparableRunsError  # noqa: E402

import cli.main as m  # noqa: E402
import cli.run as cli_run  # noqa: E402

FIXED_AT = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def _config(**overrides) -> dict:
    config = {
        "results_dir": "/tmp/results",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-6-luna",
        "deep_think_llm": "gpt-6-sol",
        "output_language": "English",
    }
    config.update(overrides)
    return config


# --- 1. stop_reason from final_state -----------------------------------------


def test_stop_reason_read_from_final_state(tmp_path):
    path = cli_run.write_run_manifest(
        config=_config(results_dir=str(tmp_path)),
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome="Buy",
        usage={"llm_calls": 1, "tool_calls": 0, "tokens_in": 1, "tokens_out": 0},
        duration_seconds=1.0,
        failure=None,
        variant="v0",
        repeat=1,
        at=FIXED_AT,
        version="0.7.1",
        stop_reason="completed",
    )
    from tradingagents.run_recorder import read_manifest

    assert read_manifest(path)["stop_reason"] == "completed"


def test_stop_reason_none_fallback(tmp_path):
    path = cli_run.write_run_manifest(
        config=_config(results_dir=str(tmp_path)),
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome=None,
        usage={"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0},
        duration_seconds=None,
        failure=None,
        variant="v0",
        repeat=1,
        at=FIXED_AT,
        version="0.7.1",
    )
    from tradingagents.run_recorder import read_manifest

    assert read_manifest(path)["stop_reason"] is None


def test_finalize_reads_stop_reason_from_final_state(tmp_path):
    captured = {}

    def write(**kw):
        captured.update(kw)
        return tmp_path / "manifest.json"

    class _Graph:
        def record_decision(self, *a, **k):
            pass

        def clear_checkpoint_on_success(self, *a, **k):
            pass

    cli_run._finalize_run_manifest(
        write=write,
        graph=_Graph(),
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        portfolio=None,
        final_state={"final_trade_decision": "Buy", "stop_reason": "REVIEW_REQUIRED"},
        failure=None,
    )
    assert captured["stop_reason"] == "REVIEW_REQUIRED"


def test_finalize_stop_reason_none_when_absent():
    captured = {}

    class _Graph:
        def record_decision(self, *a, **k):
            pass

        def clear_checkpoint_on_success(self, *a, **k):
            pass

    cli_run._finalize_run_manifest(
        write=lambda **kw: captured.update(kw),
        graph=_Graph(),
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        portfolio=None,
        final_state={"final_trade_decision": "Buy"},
        failure=None,
    )
    assert captured["stop_reason"] is None


def test_finalize_failure_has_null_stop_reason():
    captured = {}

    class _Graph:
        def record_decision(self, *a, **k):
            raise AssertionError("record_decision must not run on failure")

        def clear_checkpoint_on_success(self, *a, **k):
            raise AssertionError("checkpoint must be kept on failure")

    with pytest.raises(RuntimeError):
        cli_run._finalize_run_manifest(
            write=lambda **kw: captured.update(kw),
            graph=_Graph(),
            ticker="NVDA",
            trade_date="2026-11-20",
            asset_type="stock",
            portfolio=None,
            final_state=None,
            failure=RuntimeError("boom"),
        )
    assert captured["stop_reason"] is None


# --- 2. v1/v2 rejected before any model call ---------------------------------


def test_reject_helper_allows_v0():
    cli_run._reject_unavailable_variant("v0", config={})  # must not raise


@pytest.mark.parametrize("variant", ["v1", "v2"])
def test_reject_helper_refuses_non_v0_without_workflow_variant(variant):
    with pytest.raises(cli_run.typer.Exit):
        cli_run._reject_unavailable_variant(variant, config={})


@pytest.mark.parametrize("variant", ["v1", "v2"])
def test_reject_helper_allows_when_workflow_variant_present(variant):
    cli_run._reject_unavailable_variant(variant, config={"workflow_variant": variant})


def test_run_analysis_rejects_v1_before_model_call(monkeypatch):
    started = []
    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *a, **k: started.append(True))
    with pytest.raises(cli_run.typer.Exit):
        cli_run.run_analysis(flags={}, variant="v1")
    assert started == []


def test_cli_variant_v1_exits_nonzero(monkeypatch):
    calls = []
    monkeypatch.setattr(m, "run_analysis", lambda **kw: calls.append(kw))
    result = CliRunner().invoke(m.app, ["--variant", "v1"])
    assert result.exit_code != 0
    assert calls == []


# --- 4. missing usage stays null ---------------------------------------------


def _manifest(usage="__default__", **overrides):
    base = {
        "schema_version": 1,
        "run_id": "v0-nvda-2026-11-20-r1-20261121t1200",
        "created_at": "2026-11-21T12:00:00+00:00",
        "version": "0.7.1",
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
        "outcome": "Buy",
        "config_snapshot": dict(_config()),
        "prompt_hashes": {"market": "sha256:aaa"},
        "evidence_snapshot": None,
        "usage": {"llm_calls": 1, "tool_calls": 0, "tokens_in": 10, "tokens_out": 5},
        "duration_seconds": 1.0,
        "failure": None,
        "stop_reason": None,
    }
    if usage != "__default__":
        base["usage"] = usage
    base.update(overrides)
    return base


def test_compare_missing_usage_is_null_not_zero():

    a = _manifest(usage=None, run_id="v0-nvda-2026-11-20-r1-20261121t1200")
    b = _manifest(usage={"llm_calls": 10, "tool_calls": 2, "tokens_in": 100, "tokens_out": 50},
                  run_id="v0-nvda-2026-11-20-r2-20261121t1300")
    comparison = compare_runs.compare_manifests([a, b])
    row_a = next(r for r in comparison.variants if r["run_id"] == a["run_id"])
    assert row_a["usage"] is None
    # Average counts only the run that reported usage; it does not treat null as 0.
    assert comparison.averages["v0"]["llm_calls"] == pytest.approx(10.0)


def test_compare_all_missing_usage_average_is_null():

    a = _manifest(usage=None, run_id="v0-nvda-2026-11-20-r1-20261121t1200")
    comparison = compare_runs.compare_manifests([a])
    assert comparison.averages["v0"]["llm_calls"] is None
    assert comparison.averages["v0"]["tokens_in"] is None


# --- 3. compare_runs refuses empty prompt_hashes -----------------------------


def test_compare_refuses_empty_prompt_hashes():

    a = _manifest(prompt_hashes={}, run_id="v0-nvda-2026-11-20-r1-20261121t1200")
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifests([a])
    assert "prompt_hashes" in str(exc.value)


def test_compare_refuses_none_prompt_hashes():

    a = _manifest(prompt_hashes=None, run_id="v0-nvda-2026-11-20-r1-20261121t1200")
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifests([a])
    assert "prompt_hashes" in str(exc.value)


def test_compare_refuses_when_one_prompt_hashes_empty():

    a = _manifest(prompt_hashes={"market": "sha256:aaa"}, run_id="v0-nvda-2026-11-20-r1-20261121t1200")
    b = _manifest(prompt_hashes={}, run_id="v0-nvda-2026-11-20-r2-20261121t1300")
    with pytest.raises(IncomparableRunsError):
        compare_runs.compare_manifests([a, b])
