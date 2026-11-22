"""Exercise the explicit resume entry point against an interrupted SQLite run."""

import sqlite3
from contextlib import closing
from types import SimpleNamespace
from typing import TypedDict
from unittest.mock import Mock

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from tradingagents.dataflows.config import get_config
from tradingagents.graph import trading_graph
from tradingagents.graph.checkpointer import thread_id
from tradingagents.graph.propagation import Propagator
from tradingagents.graph.trading_graph import CheckpointResumePreflightError, TradingAgentsGraph

pytestmark = pytest.mark.unit
TICKER = "NVDA"
DATE = "2026-01-09"
RUN_ID = "original"


class _State(TypedDict, total=False):
    count: int
    final_rating: str


@pytest.fixture
def interrupted(tmp_path, monkeypatch):
    script = SimpleNamespace(calls=[], interrupt=True)
    graph = object.__new__(TradingAgentsGraph)
    graph.config = {
        "checkpoint_enabled": True,
        "data_cache_dir": str(tmp_path / "current"),
        "max_debate_rounds": 2,
        "max_risk_discuss_rounds": 1,
        "output_language": "French",
    }
    graph._workflow_variant = "v0"
    graph.selected_analysts = ("market",)
    graph.propagator = Propagator(max_recur_limit=20)

    def analyst(state: _State):
        script.calls.append(("analyst", state["count"]))
        return {"count": state["count"] + 1}

    def trader(state: _State):
        script.calls.append(("trader", state["count"]))
        if script.interrupt:
            raise RuntimeError("scripted interruption")
        assert get_config()["output_language"] == "French"
        return {"count": state["count"] + 10, "final_rating": "Hold"}

    workflow = StateGraph(_State)
    workflow.add_node("analyst", analyst)
    workflow.add_node("trader", trader)
    workflow.add_edge(START, "analyst")
    workflow.add_edge("analyst", "trader")
    workflow.add_edge("trader", END)
    graph.workflow = workflow
    plain_graph = graph.graph = workflow.compile()

    db = tmp_path / "original run #1.db"
    signature = graph._run_signature("stock")
    original, neighbor, legacy = (
        thread_id(TICKER, DATE, signature, run_key=key) for key in (RUN_ID, "neighbor", "")
    )
    with closing(sqlite3.connect(db, check_same_thread=False)) as conn:
        compiled = workflow.compile(checkpointer=SqliteSaver(conn))
        for tid, count in [(original, 1), (neighbor, 20), (legacy, 100)]:
            script.calls.clear()
            with pytest.raises(RuntimeError, match="scripted interruption"):
                compiled.invoke({"count": count}, config={"configurable": {"thread_id": tid}})
            assert script.calls == [("analyst", count), ("trader", count + 1)]

    script.calls.clear()
    script.interrupt = False
    for name in ("create_run_state", "record_decision", "save_reports", "clear_checkpoint_on_success"):
        monkeypatch.setattr(graph, name, Mock(side_effect=AssertionError(name)))
    compile_spy = Mock(wraps=workflow.compile)
    monkeypatch.setattr(workflow, "compile", compile_spy)
    return SimpleNamespace(
        graph=graph, db=db, original=original, neighbor=neighbor, legacy=legacy,
        script=script, compile=compile_spy, plain_graph=plain_graph,
    )


def _resume(run, **kwargs):
    target = {"db": run.db, "recorded_thread_id": run.original, "run_id": RUN_ID}
    return run.graph.resume_checkpoint(TICKER, DATE, **(target | kwargs))


def _rows(db, *, tid=None):
    with closing(sqlite3.connect(db)) as conn:
        return {
            table: set(conn.execute(
                f"SELECT * FROM {table}" + (" WHERE thread_id = ?" if tid is not None else ""),
                () if tid is None else (tid,),
            ))
            for table in ("checkpoints", "writes")
        }


def _assert_execution_connection_closed(run):
    run.compile.assert_called_once()
    saver = run.compile.call_args.kwargs["checkpointer"]
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        saver.conn.execute("SELECT 1")


def test_resumes_pending_node_and_keeps_all_threads(interrupted):
    """Provisional: REQ-C-LOCAL-CKPT-007 and INV-C-LOCAL-CKPT-007."""
    run = interrupted
    siblings = {tid: _rows(run.db, tid=tid) for tid in (run.neighbor, run.legacy)}
    before = _rows(run.db, tid=run.original)
    state, signal = _resume(run)

    assert run.script.calls == [("trader", 2)]
    assert state == {"count": 12, "final_rating": "Hold"}
    assert signal == "Hold"
    assert run.graph.graph is run.plain_graph
    assert not (run.db.parent / "current").exists()
    after = _rows(run.db, tid=run.original)
    assert before["checkpoints"] < after["checkpoints"]
    assert before["writes"] <= after["writes"]
    assert {tid: _rows(run.db, tid=tid) for tid in siblings} == siblings
    assert {
        table: {row[0] for row in rows} for table, rows in _rows(run.db).items()
    } == dict.fromkeys(("checkpoints", "writes"), {run.original, run.neighbor, run.legacy})
    _assert_execution_connection_closed(run)


def test_signature_mismatch_runs_no_nodes(interrupted, monkeypatch):
    """Provisional: INV-C-LOCAL-CKPT-007."""
    run = interrupted
    before = _rows(run.db)
    lookup = Mock(side_effect=AssertionError("mismatch must not read SQLite"))
    monkeypatch.setattr(trading_graph, "checkpoint_thread_exists", lookup)

    with pytest.raises(CheckpointResumePreflightError) as exc:
        _resume(run, asset_type="crypto")

    assert exc.value.code == "checkpoint_signature_mismatch"
    lookup.assert_not_called()
    run.compile.assert_not_called()
    assert run.script.calls == []
    assert _rows(run.db) == before


@pytest.mark.parametrize("remove_database", [False, True], ids=["thread", "database"])
def test_target_disappears_after_preflight(interrupted, monkeypatch, remove_database):
    """Provisional: INV-C-LOCAL-CKPT-007."""
    run = interrupted
    preflight = trading_graph.preflight_checkpoint_resume
    survivors = {}

    def preflight_then_remove(**kwargs):
        verified = preflight(**kwargs)
        if remove_database:
            run.db.unlink()
        else:
            with closing(sqlite3.connect(run.db)) as conn, conn:
                conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (verified,))
                conn.execute("DELETE FROM writes WHERE thread_id = ?", (verified,))
            survivors.update(_rows(run.db))
        return verified

    monkeypatch.setattr(trading_graph, "preflight_checkpoint_resume", preflight_then_remove)
    with pytest.raises(CheckpointResumePreflightError) as exc:
        _resume(run)

    assert exc.value.code == "checkpoint_not_found"
    assert run.script.calls == []
    if remove_database:
        assert not run.db.exists()
        run.compile.assert_not_called()
    else:
        assert _rows(run.db) == survivors
        _assert_execution_connection_closed(run)


def test_closes_execution_connection_when_pending_node_fails(interrupted):
    """Provisional: INV-C-LOCAL-CKPT-007."""
    run = interrupted
    run.script.interrupt = True
    with pytest.raises(RuntimeError, match="scripted interruption"):
        _resume(run)

    assert run.script.calls == [("trader", 2)]
    assert run.graph.graph is run.plain_graph
    assert _rows(run.db, tid=run.original)["checkpoints"]
    _assert_execution_connection_closed(run)
