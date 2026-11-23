"""Tests for review: programmatic guard opt-in (D-to-C-open-items-ruling.md §5)."""

import pytest
from langchain_core.runnables import RunnableLambda
from pydantic import Field

from tests import test_graph_end_to_end as graph_fixture

pytestmark = pytest.mark.unit
offline = graph_fixture.offline


class GuardScriptedModel(graph_fixture.ScriptedModel):
    """Script model output only; record the real PM's structured invocation."""

    pm_nodes: list[str] = Field(default_factory=list)

    def with_structured_output(self, schema, **kwargs):
        if schema is not graph_fixture.schemas.PortfolioDecision:
            return super().with_structured_output(schema, **kwargs)

        def decide(prompt, config):
            self._count()
            self.pm_nodes.append(config["metadata"]["langgraph_node"])
            return graph_fixture.STRUCTURED[schema]

        return RunnableLambda(decide)


def _run(tmp_path, monkeypatch, **config):
    model = GuardScriptedModel(structured=True, cache=False)
    graph = graph_fixture._graph(
        tmp_path, monkeypatch, model, checkpoint_enabled=False, **config
    )
    state, signal = graph.propagate("NVDA", graph_fixture.TRADE_DATE)
    assert model.pm_nodes == ["Portfolio Manager"]
    assert state["risk_debate_state"]["latest_speaker"] == "Judge"
    assert state["investment_plan"].strip() and state["trader_investment_plan"].strip()
    # The real Trader emits a rendered plan, not the guard's separate proposal
    # dictionary. No book was supplied. Do not synthesize either input.
    assert "trader_proposal" not in state
    assert "portfolio" not in state
    return state, signal


def test_explicit_guard_opt_in_exposes_final_guard_result(tmp_path, monkeypatch, offline):
    """INV-D6 / REQ-D-007: missing guard inputs block, not silently bypass."""
    state, _ = _run(tmp_path, monkeypatch, guard_enabled=True)

    assert "guard_result" in state, "guard_enabled=True did not yield a final guard_result"
    assert state["guard_enabled"] is True
    result = state["guard_result"]
    assert result["contract"] == "validation-decision/1.1"
    assert result["verdict"] == "BLOCK"
    assert result["checkpoint"] == "pm"
    assert result["executable"] is False
    assert result["rules_hit"] == [
        {"checkpoint": "trader", "reason_code": "MISSING_FIELD"},
        {"checkpoint": "pm", "reason_code": "OVERRIDE_REJECTED"},
    ]


def test_omitted_guard_opt_in_keeps_legacy_run_and_state(tmp_path, monkeypatch, offline):
    """Validation-decision v1.1 legacy comparator: absence must stay absent."""
    state, signal = _run(tmp_path, monkeypatch)

    assert signal == state["final_rating"] == "Overweight"
    assert "**Rating**: Overweight" in state["final_trade_decision"]
    assert "guard_enabled" not in state
    assert "guard_result" not in state
