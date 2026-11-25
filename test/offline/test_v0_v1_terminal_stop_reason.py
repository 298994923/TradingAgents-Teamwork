"""Tests for review: C's top-level terminal reason reaches the real CLI manifest."""

import hashlib
import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from functools import wraps
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import cli.run as cli_run
from cli.main import app
from cli.models import AnalystType
from tests import test_graph_end_to_end as graph_fixture
from tradingagents.run_recorder import read_manifest

pytestmark = pytest.mark.unit
offline = graph_fixture.offline


def _run_cli(monkeypatch, tmp_path, variant, *, guard=False, fail=False):
    monkeypatch.setattr(cli_run, "unattended_gaps", lambda flags: [])
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags: {
        "ticker": "NVDA", "analysis_date": graph_fixture.TRADE_DATE, "asset_type": "stock",
        "analysts": [AnalystType.MARKET], "research_depth": 3, "llm_provider": "openai",
        "quick_think_llm": "offline", "deep_think_llm": "offline", "backend_url": None,
    })
    monkeypatch.setattr(cli_run, "message_buffer", type(cli_run.message_buffer)())
    config = deepcopy(cli_run.DEFAULT_CONFIG)
    config.update(
        results_dir=str(tmp_path / "results"), data_cache_dir=str(tmp_path / "cache"),
        memory_log_path=str(tmp_path / "memory.md"), max_risk_discuss_rounds=1,
        guard_enabled=guard,
    )
    monkeypatch.setattr(cli_run, "DEFAULT_CONFIG", config)
    monkeypatch.delenv("TRADINGAGENTS_MAX_DEBATE_ROUNDS", raising=False)
    monkeypatch.setenv("TRADINGAGENTS_MAX_RISK_ROUNDS", "1")
    model = graph_fixture.TimedModel(cache=False, fail_at=1 if fail else None)
    monkeypatch.setattr(
        graph_fixture.trading_graph, "create_tier_client",
        lambda *args, **kwargs: graph_fixture._Client(model),
    )
    observations = []
    finalize = cli_run._finalize_run_manifest

    @wraps(finalize)
    def observe(**kwargs):
        # Read-only observation of the real stream's aggregate, not synthetic state.
        observations.append((deepcopy(kwargs["final_state"]), kwargs["failure"]))
        return finalize(**kwargs)

    monkeypatch.setattr(cli_run, "_finalize_run_manifest", observe)
    result = CliRunner().invoke(app, [
        "--ticker", "NVDA", "--date", graph_fixture.TRADE_DATE, "--analysts", "market",
        "--checkpoint", "--no-save", "--no-show", "--no-html", "--variant", variant,
    ])
    if not fail and result.exception is not None:
        raise result.exception
    assert len(observations) == 1
    manifests = list((tmp_path / "results" / "runs").glob("*/manifest.json"))
    assert len(manifests) == 1
    db = tmp_path / "cache" / "checkpoints" / "NVDA.db"
    with closing(sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)) as conn:
        count = conn.execute("SELECT count(*) FROM checkpoints").fetchone()[0]
    state, failure = observations[0]
    receipt_path = manifests[0].with_name("prompt_receipts.json")
    if fail:  # The scripted first model call fails before any receipt.
        assert not receipt_path.exists()
        assert not receipt_path.with_name("prompt-receipts.jsonl").exists()
        receipts = None
    else:
        receipts = json.loads(receipt_path.read_text(encoding="utf-8"))
    return SimpleNamespace(
        result=result, state=state, failure=failure, manifest=read_manifest(manifests[0]),
        receipts=receipts, count=count, model=model,
    )


@pytest.mark.parametrize(("variant", "pairs"), [("v0", 2), ("v1", 1)])
def test_explicit_success_records_same_completed_reason(monkeypatch, tmp_path, offline, variant, pairs):
    """Provisional REQ-C-LOCAL-STOP-001: same completed reason at both boundaries."""
    run = _run_cli(monkeypatch, tmp_path, variant)
    assert run.result.exit_code == 0
    assert run.failure is None and run.manifest["failure"] is None
    assert run.state["final_rating"] == run.manifest["outcome"] == "Overweight"
    assert "guard_result" not in run.state
    assert run.count == 0
    assert run.manifest["config_snapshot"]["workflow_variant"] == variant
    nodes = [node for node, *_ in run.model.seen]
    assert [n for n in nodes if n in ("Bull Researcher", "Bear Researcher")] == [
        "Bull Researcher", "Bear Researcher",
    ] * pairs
    assert nodes[-4:] == [
        "Aggressive Analyst", "Conservative Analyst", "Neutral Analyst", "Portfolio Manager",
    ]
    roles = {"Bull Researcher": "bull", "Bear Researcher": "bear", "Research Manager": "research_manager"}
    sent = [
        (roles[node], hashlib.sha256(prompt.encode()).hexdigest())
        for node, prompt, *_ in run.model.seen if node in roles
    ]
    assert set(run.manifest["prompt_hashes"]) == set(roles.values())
    assert run.receipts["run_id"] == run.manifest["run_id"]
    assert [(call["role"], call["input_sha256"]) for call in run.receipts["calls"]] == sent
    print(
        f"{variant}: pairs={pairs}, receipts={len(sent)}, checkpoint_rows={run.count}, "
        f"state_reason={run.state.get('stop_reason')!r}, manifest_reason={run.manifest['stop_reason']!r}"
    )
    assert (run.state.get("stop_reason"), run.manifest["stop_reason"]) == ("completed", "completed")


def test_exception_writes_failure_and_null_stop_reason(monkeypatch, tmp_path, offline):
    """Provisional INV-C-LOCAL-STOP-001: an exception is never normal completion."""
    run = _run_cli(monkeypatch, tmp_path, "v1", fail=True)
    assert run.result.exit_code != 0
    assert isinstance(run.failure, RuntimeError)
    assert str(run.failure) == run.manifest["failure"] == "provider unavailable"
    assert run.state is None
    assert run.manifest["stop_reason"] is None
    assert run.count > 0
    print("exception: failure='provider unavailable', state absent, stop_reason=null, checkpoint retained")


def test_guard_block_is_not_completed(monkeypatch, tmp_path, offline):
    """Provisional INV-C-LOCAL-STOP-001: do not invent a Guard stop-code mapping."""
    run = _run_cli(monkeypatch, tmp_path, "v1", guard=True)
    assert run.result.exit_code == 0
    assert run.failure is None and run.manifest["failure"] is None
    assert run.state["final_rating"] == run.manifest["outcome"] == "REVIEW"
    assert run.state["guard_result"] == {
        "contract": "validation-decision/1.1", "verdict": "BLOCK",
        "reason_code": "OVERRIDE_REJECTED", "checkpoint": "pm", "executable": False,
        "rules_hit": [
            {"checkpoint": "trader", "reason_code": "MISSING_FIELD"},
            {"checkpoint": "pm", "reason_code": "OVERRIDE_REJECTED"},
        ],
    }
    assert run.manifest["stop_reason"] == run.state.get("stop_reason")
    assert run.manifest["stop_reason"] != "completed"
    print(f"guard: {run.state['guard_result']}, stop_reason={run.manifest['stop_reason']!r}")
