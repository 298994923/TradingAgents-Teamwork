"""Exercise programmatic checkpoint resume and cleanup with real SQLite."""

import sqlite3
from contextlib import closing
from types import SimpleNamespace
from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph

from tradingagents.graph.checkpointer import checkpoint_step, thread_id
from tradingagents.graph.trading_graph import TradingAgentsGraph

pytestmark = pytest.mark.unit
TICKER = "NVDA"
DATE = "2026-01-09"


class _State(TypedDict, total=False):
    count: int
    final_rating: str


def _scripted_graph(tmp_path, *, enabled=True):
    script = SimpleNamespace(initial_count=0, interrupt=True, calls=[], recorded=[])

    def analyst(state: _State):
        script.calls.append(("analyst", state["count"]))
        return {"count": state["count"] + 1}

    def trader(state: _State):
        script.calls.append(("trader", state["count"]))
        if script.interrupt:
            raise RuntimeError("scripted trader interruption")
        return {"count": state["count"] + 10, "final_rating": "Hold"}

    workflow = StateGraph(_State)
    workflow.add_node("analyst", analyst)
    workflow.add_node("trader", trader)
    workflow.add_edge(START, "analyst")
    workflow.add_edge("analyst", "trader")
    workflow.add_edge("trader", END)

    graph = object.__new__(TradingAgentsGraph)
    graph.config = {
        "checkpoint_enabled": enabled,
        "data_cache_dir": str(tmp_path),
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
    }
    graph.selected_analysts = ("market",)
    graph.debug = False
    graph.workflow = workflow
    graph.graph = workflow.compile()
    graph._checkpointer_ctx = None
    graph.create_run_state = lambda *_: {"count": script.initial_count}
    graph.propagator = SimpleNamespace(get_graph_args=dict)
    graph.record_decision = lambda _, __, state: script.recorded.append(state)
    return graph, script


def _interrupt(graph, script, initial_count, **kwargs):
    script.initial_count = initial_count
    script.calls.clear()
    with pytest.raises(RuntimeError, match="scripted trader interruption"):
        graph.propagate(TICKER, DATE, **kwargs)
    assert script.calls == [("analyst", initial_count), ("trader", initial_count + 1)]
    assert script.recorded == []
    assert graph._checkpointer_ctx is None


def _thread_rows(tmp_path):
    with closing(sqlite3.connect(tmp_path / "checkpoints" / f"{TICKER}.db")) as conn:
        return {
            table: {tid for (tid,) in conn.execute(f"SELECT DISTINCT thread_id FROM {table}")}
            for table in ("checkpoints", "writes")
        }


def test_keyed_propagate_resumes_and_cleans_up_only_its_thread(tmp_path):
    """Provisional: REQ-C-LOCAL-CKPT-004 and INV-C-LOCAL-CKPT-004."""
    graph, script = _scripted_graph(tmp_path)
    signature = graph._run_signature("stock")
    identity = (TICKER, DATE, signature)
    legacy, r1, r2 = (thread_id(*identity, run_key=key) for key in ("", "r1", "r2"))

    # A saved legacy checkpoint must not be used as the input for either keyed run.
    _interrupt(graph, script, 100)
    _interrupt(graph, script, 1, run_key="r1")
    saved_step = checkpoint_step(tmp_path, *identity, run_key="r1")
    assert saved_step == 1  # analyst has finished; trader is pending
    _interrupt(graph, script, 20, run_key="r2")
    assert graph._run_signature("stock") == signature
    assert _thread_rows(tmp_path) == dict.fromkeys(("checkpoints", "writes"), {legacy, r1, r2})

    script.initial_count = 999  # must not replace the saved input
    script.interrupt = False
    script.calls.clear()
    state, rating = graph.propagate(TICKER, DATE, run_key="r1")

    assert script.calls == [("trader", 2)]
    assert state["count"] == 12
    assert rating == "Hold"
    assert script.recorded == [state]
    assert graph._checkpointer_ctx is None
    assert checkpoint_step(tmp_path, *identity, run_key="r1") is None
    assert checkpoint_step(tmp_path, *identity, run_key="r2") == saved_step
    assert checkpoint_step(tmp_path, *identity) == saved_step
    assert _thread_rows(tmp_path) == dict.fromkeys(("checkpoints", "writes"), {legacy, r2})


def test_omitted_key_resumes_and_cleans_up_legacy_thread(tmp_path):
    """Provisional: INV-C-LOCAL-CKPT-004."""
    graph, script = _scripted_graph(tmp_path)
    identity = (TICKER, DATE, graph._run_signature("stock"))
    _interrupt(graph, script, 0)
    legacy = thread_id(*identity)
    assert _thread_rows(tmp_path) == dict.fromkeys(("checkpoints", "writes"), {legacy})

    script.interrupt = False
    script.calls.clear()
    state, _ = graph.propagate(TICKER, DATE)

    assert script.calls == [("trader", 1)]
    assert state["count"] == 11
    assert checkpoint_step(tmp_path, *identity) is None
    assert _thread_rows(tmp_path) == {"checkpoints": set(), "writes": set()}


@pytest.mark.parametrize("kwargs", [{}, {"run_key": "r1"}], ids=["omitted", "keyed"])
def test_disabled_checkpointing_does_not_open_sqlite(tmp_path, kwargs):
    """Provisional: INV-C-LOCAL-CKPT-004."""
    graph, script = _scripted_graph(tmp_path, enabled=False)
    plain_graph = graph.graph
    _interrupt(graph, script, 0, **kwargs)
    script.initial_count = 10
    script.interrupt = False
    script.calls.clear()

    state, _ = graph.propagate(TICKER, DATE, **kwargs)

    assert script.calls == [("analyst", 10), ("trader", 11)]
    assert state["count"] == 21
    assert graph.graph is plain_graph
    assert not (tmp_path / "checkpoints").exists()
