"""FR-REVIEW: compact repeated history before sending and recording a debate prompt."""

from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
from tradingagents.agents.researchers.bull_researcher import create_bull_researcher


@pytest.mark.parametrize("factory", [create_bull_researcher, create_bear_researcher])
def test_researcher_compacts_history_and_receipts_match_sent_input(factory):
    repeat = "Earlier discussion: the historical example has already been considered."
    history = "\n".join([repeat] * 700)
    target = "Current opposing point: the latest margin fell despite rising sales."
    receipts = []
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(content="New argument.")
    state = {
        "company_of_interest": "NVDA",
        "market_report": "Forecast EPS -5",
        "sentiment_report": "",
        "news_report": "Forecast EPS 5",
        "fundamentals_report": "",
        "investment_debate_state": {
            "history": history,
            "current_response": target,
            "count": 4,
        },
    }

    result = factory(llm, on_prompt=receipts.append)(state)
    llm.invoke.assert_called_once()
    sent = llm.invoke.call_args.args[0]
    assert target in sent
    assert "Market research report: Forecast EPS -5" in sent
    assert "Latest world affairs news: Forecast EPS 5" in sent
    assert sent.count(repeat) <= 1
    assert result["investment_debate_state"]["history"].startswith(history + "\n")
    assert [receipt["input_sha256"] for receipt in receipts] == [
        sha256(sent.encode("utf-8")).hexdigest()
    ]


def test_manager_keeps_latest_arguments_from_both_sides():
    from tradingagents.agents.managers.research_manager import create_research_manager

    old = "Bull Analyst: Earlier view no longer material."
    bull = "Bull Analyst: Latest bull argument with supporting evidence."
    bear = "Bear Analyst: Latest bear argument with supporting evidence."
    history = "\n".join([old] * 900 + [bull, bear])
    receipts = []
    llm = Mock()
    llm.with_structured_output.side_effect = NotImplementedError
    llm.invoke.return_value = SimpleNamespace(content="Recommendation: Hold")
    state = {
        "company_of_interest": "NVDA",
        "investment_debate_state": {"history": history, "count": 4},
    }

    result = create_research_manager(llm, on_prompt=receipts.append)(state)
    sent = llm.invoke.call_args.args[0]
    assert sent.count(old) <= 1
    assert sent.index(bull) < sent.index(bear)
    assert result["investment_debate_state"]["history"] == history
    assert [receipt["input_sha256"] for receipt in receipts] == [
        sha256(sent.encode("utf-8")).hexdigest()
    ]


def test_required_context_over_budget_stops_before_call_or_receipt():
    from tradingagents.context_builder import ContextBudgetError

    receipts = []
    llm = Mock()
    state = {
        "company_of_interest": "NVDA",
        "market_report": "",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "investment_debate_state": {"current_response": "x" * 40000, "count": 4},
    }

    with pytest.raises(ContextBudgetError):
        create_bull_researcher(llm, on_prompt=receipts.append)(state)
    llm.invoke.assert_not_called()
    assert receipts == []
