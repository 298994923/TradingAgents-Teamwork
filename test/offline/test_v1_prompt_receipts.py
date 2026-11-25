"""Verify that fixed pruning changes debate depth without dropping B's receipts."""

import hashlib
from functools import partial

import pytest

from tests import test_graph_end_to_end as graph_fixture

graph_offline = graph_fixture.offline

DEBATE_ROLES = {
    "Bull Researcher": "bull",
    "Bear Researcher": "bear",
    "Research Manager": "research_manager",
}
RISK_ROUTE = ["Aggressive Analyst", "Conservative Analyst", "Neutral Analyst"]


@pytest.mark.unit
@pytest.mark.usefixtures("graph_offline")
@pytest.mark.parametrize(
    ("selector_kwargs", "depth"),
    [({}, 3), ({"workflow_variant": "v0"}, 2), ({"workflow_variant": "v1"}, 1)],
    ids=["omitted", "v0", "v1"],
)
def test_selector_preserves_prompt_receipts_and_risk_route(
    tmp_path, monkeypatch, selector_kwargs, depth
):
    """Provisional: REQ-C-LOCAL-V1-001 and INV-C-LOCAL-V1-001."""
    receipts = []
    model = graph_fixture.TimedModel(cache=False)
    graph_module = graph_fixture.trading_graph
    # Pass constructor keywords through the shared fixture, without replacing
    # the real constructor, observer forwarding, or runtime receipt machinery.
    with monkeypatch.context() as constructor_patch:
        constructor_patch.setattr(
            graph_module,
            "TradingAgentsGraph",
            partial(graph_module.TradingAgentsGraph, on_prompt=receipts.append, **selector_kwargs),
        )
        graph = graph_fixture._graph(
            tmp_path, monkeypatch, model,
            checkpoint_enabled=False, max_debate_rounds=3, max_risk_discuss_rounds=1,
        )

    state, signal = graph.propagate("NVDA", graph_fixture.TRADE_DATE)

    debate_nodes = ["Bull Researcher", "Bear Researcher"] * depth + ["Research Manager"]
    assert [step for step, *_ in model.seen if step != "agent"] == [
        *debate_nodes, "Trader", *RISK_ROUTE, "Portfolio Manager",
    ]
    assert signal == state["final_rating"] == "Overweight"
    assert [receipt["role"] for receipt in receipts] == [
        DEBATE_ROLES[step] for step in debate_nodes
    ]
    sent = [
        (DEBATE_ROLES[step], hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        for step, prompt, *_ in model.seen
        if step in DEBATE_ROLES
    ]
    assert [(receipt["role"], receipt["input_sha256"]) for receipt in receipts] == sent
