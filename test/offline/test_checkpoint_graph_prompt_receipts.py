"""Keep the legacy graph route and B's prompt receipts intact across checkpoint changes."""

import hashlib
from functools import partial

import pytest

from tests import test_graph_end_to_end as graph_fixture

graph_offline = graph_fixture.offline


@pytest.mark.unit
@pytest.mark.usefixtures("graph_offline")
def test_unkeyed_checkpoint_route_preserves_real_prompt_receipts(tmp_path, monkeypatch):
    """Provisional: INV-C-LOCAL-CKPT-004 (legacy graph behavior)."""
    receipts = []
    model = graph_fixture.TimedModel(cache=False)
    graph_module = graph_fixture.trading_graph
    # The shared fixture has no constructor kwargs for the observer. Inject only
    # that argument while it constructs the real graph; leave runtime wiring alone.
    with monkeypatch.context() as constructor_patch:
        constructor_patch.setattr(
            graph_module, "TradingAgentsGraph",
            partial(graph_module.TradingAgentsGraph, on_prompt=receipts.append),
        )
        graph = graph_fixture._graph(
            tmp_path, monkeypatch, model, checkpoint_enabled=True,
            max_debate_rounds=1, max_risk_discuss_rounds=1,
        )

    state, signal = graph.propagate("NVDA", graph_fixture.TRADE_DATE)

    role_nodes = {
        "Bull Researcher": "bull",
        "Bear Researcher": "bear",
        "Research Manager": "research_manager",
    }
    assert [step for step, *_ in model.seen if step != "agent"] == [
        *role_nodes, "Trader", "Aggressive Analyst", "Conservative Analyst",
        "Neutral Analyst", "Portfolio Manager",
    ]
    assert all(
        state[key].strip()
        for key in ("market_report", "sentiment_report", "news_report", "fundamentals_report")
    )
    assert signal == state["final_rating"] == "Overweight"
    assert [receipt["role"] for receipt in receipts] == list(role_nodes.values())
    sent = [
        (role_nodes[step], hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        for step, prompt, *_ in model.seen
        if step in role_nodes
    ]
    assert [(receipt["role"], receipt["input_sha256"]) for receipt in receipts] == sent
    for receipt in receipts:
        hashes = receipt["prompt_hashes"]
        assert list(hashes) == [f"b.{receipt['role']}"]
        digest = next(iter(hashes.values()))
        assert len(digest) == 64 and set(digest) <= set("0123456789abcdef")
