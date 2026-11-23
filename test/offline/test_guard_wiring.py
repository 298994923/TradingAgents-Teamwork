"""Offline wiring tests for the deterministic guard in the Portfolio Manager node.

These tests define the opt-in guarded-mode contract (``state["guard_enabled"]``)
and the structured state inputs (``state["portfolio"]`` and
``state["trader_proposal"]``). They use only scripted in-process LLM stubs: no
network, no real provider calls.

Every test cites INV-D6 / INV-D7 / INV-D8 / REQ-D-007.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace


def _load_portfolio_manager_for_offline_test():
    """Load the real PM module without importing optional heavy agent deps.

    The PM wiring is the unit under test. The package ``__init__`` imports every
    analyst, which pulls in LangChain/provider packages that are irrelevant to
    this offline guard test. Only the prompt-context helper is stubbed; the PM
    module, rating parser, schemas, and structured helper are the real files.
    """
    import tradingagents

    agents_dir = Path(tradingagents.__file__).resolve().parent / "agents"

    context_stub = types.ModuleType("tradingagents.agents.context")
    context_stub.get_instrument_context_from_state = lambda state: "Instrument context."
    context_stub.get_language_instruction = lambda: ""
    context_stub.get_portfolio_context_from_state = lambda state: "Portfolio context."

    fake_agents_pkg = types.ModuleType("tradingagents.agents")
    fake_agents_pkg.__path__ = [str(agents_dir)]

    names = ("tradingagents.agents", "tradingagents.agents.context")
    saved = {name: sys.modules.get(name) for name in names}
    sys.modules["tradingagents.agents"] = fake_agents_pkg
    sys.modules["tradingagents.agents.context"] = context_stub
    try:
        from tradingagents.agents.schemas import PortfolioDecision, PortfolioRating

        spec = importlib.util.spec_from_file_location(
            "_portfolio_manager_under_test",
            agents_dir / "managers" / "portfolio_manager.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous

    return module.create_portfolio_manager, PortfolioDecision, PortfolioRating


create_portfolio_manager, PortfolioDecision, PortfolioRating = (
    _load_portfolio_manager_for_offline_test()
)

_UNSET = object()

RISK_STATE = {
    "history": "Risk debate history.",
    "aggressive_history": "",
    "conservative_history": "",
    "neutral_history": "",
    "current_aggressive_response": "",
    "current_conservative_response": "",
    "current_neutral_response": "",
    "latest_speaker": "Neutral",
    "count": 1,
}

VALID_TRADER_PROPOSAL = {
    "ticker": "AAPL",
    "action": "Buy",
    "delta_quantity": 10,
    "price": 100,
}

OVER_CAP_TRADER_PROPOSAL = {
    "ticker": "AAPL",
    "action": "Buy",
    "delta_quantity": 101,
    "price": 100,
}

KNOWN_PORTFOLIO = {"nav": 100000, "currency": "USD", "positions": []}

TRADEABLE_TOKENS = ("Buy", "Overweight", "Hold", "Underweight", "Sell")


class _StructuredLLM:
    """Scripted structured-output LLM; returns one fixed decision."""

    def __init__(self, decision):
        self.decision = decision
        self.calls: list[object] = []

    def with_structured_output(self, *args, **kwargs):
        return self

    def invoke(self, prompt, *args, **kwargs):
        self.calls.append(prompt)
        return self.decision


def _state(
    *,
    trader_proposal=None,
    portfolio=_UNSET,
    investment_plan="Research plan.",
    trader_plan="Trader plan.",
    guard_enabled=True,
):
    state = {
        "company_of_interest": "AAPL",
        "risk_debate_state": dict(RISK_STATE),
        "investment_plan": investment_plan,
        "trader_investment_plan": trader_plan,
        "guard_enabled": guard_enabled,
    }
    if trader_proposal is not None:
        state["trader_proposal"] = trader_proposal
    if portfolio is not _UNSET:
        state["portfolio"] = portfolio
    return state


def _valid_pm_decision():
    return PortfolioDecision(
        rating=PortfolioRating.BUY,
        executive_summary="Build the position in the analyzed instrument.",
        investment_thesis="The risk debate supports the trade.",
    )


def _invalid_rating_decision():
    return SimpleNamespace(
        rating=SimpleNamespace(value="Strong Buy"),
        executive_summary="Use an alias rating.",
        investment_thesis="This rating is outside the canonical domain.",
        price_target=None,
        time_horizon=None,
    )


def test_trader_over_cap_blocks_and_suppresses_output():
    """INV-D6 / REQ-D-007: a Trader plan over the cap is BLOCK and non-executable."""
    result = create_portfolio_manager(_StructuredLLM(_valid_pm_decision()))(
        _state(
            trader_proposal=OVER_CAP_TRADER_PROPOSAL,
            portfolio=KNOWN_PORTFOLIO,
        )
    )

    assert result["guard_verdict"] == "BLOCK"
    assert result["guard_trader"]["verdict"] == "BLOCK"
    assert result["guard_trader"]["reason_code"] == "CAP_EXCEEDED"
    assert result["final_rating"] == "REVIEW"
    assert result["guard_executable"] is False

    decision = result["final_trade_decision"]
    assert "**Rating**" not in decision
    assert not any(token in decision for token in TRADEABLE_TOKENS)


def test_pm_invalid_rating_blocks_at_final_gate():
    """INV-D6 / REQ-D-007: the PM gate rejects a non-canonical rating alias."""
    result = create_portfolio_manager(_StructuredLLM(_invalid_rating_decision()))(
        _state(trader_proposal=VALID_TRADER_PROPOSAL, portfolio=KNOWN_PORTFOLIO)
    )

    assert result["guard_verdict"] == "BLOCK"
    assert result["guard_pm"]["verdict"] == "BLOCK"
    assert result["guard_pm"]["reason_code"] == "INVALID_RATING"
    assert result["final_rating"] == "REVIEW"
    assert result["guard_executable"] is False
    assert "Strong Buy" not in result["final_trade_decision"]
    assert "**Rating**" not in result["final_trade_decision"]


def test_valid_trader_and_pm_decision_passes_executable():
    """INV-D6 / REQ-D-007: both gates passing yields an executable final decision."""
    result = create_portfolio_manager(_StructuredLLM(_valid_pm_decision()))(
        _state(trader_proposal=VALID_TRADER_PROPOSAL, portfolio=KNOWN_PORTFOLIO)
    )

    assert result["guard_verdict"] == "PASS"
    assert result["guard_executable"] is True
    assert result["final_rating"] == "Buy"
    assert "**Rating**: Buy" in result["final_trade_decision"]


def test_trader_block_survives_valid_looking_pm_decision():
    """INV-D7 / REQ-D-007: PM text cannot lower an earlier Trader BLOCK."""
    result = create_portfolio_manager(_StructuredLLM(_valid_pm_decision()))(
        _state(
            trader_proposal=OVER_CAP_TRADER_PROPOSAL,
            portfolio=KNOWN_PORTFOLIO,
        )
    )

    assert result["guard_verdict"] == "BLOCK"
    assert result["guard_pm"]["verdict"] == "BLOCK"
    assert result["guard_pm"]["reason_code"] == "OVERRIDE_REJECTED"
    assert result["guard_pm"]["details"].get("override_rejected") is True
    assert result["final_rating"] == "REVIEW"
    assert result["guard_executable"] is False
    assert "**Rating**" not in result["final_trade_decision"]


def test_absent_structured_portfolio_reviews_non_executable():
    """INV-D8 / REQ-D-007: absent structured portfolio is REVIEW, never flat."""
    result = create_portfolio_manager(_StructuredLLM(_valid_pm_decision()))(
        _state(trader_proposal=VALID_TRADER_PROPOSAL)
    )

    assert result["guard_verdict"] == "REVIEW"
    assert result["guard_reason_code"] == "POSITION_UNKNOWN"
    assert result["guard_trader"]["verdict"] == "REVIEW"
    assert result["guard_trader"]["reason_code"] == "POSITION_UNKNOWN"
    assert result["final_rating"] == "REVIEW"
    assert result["guard_executable"] is False


def test_missing_plans_are_unavailable_and_never_fabricated():
    """INV-D8 / REQ-D-007: absent plans are explicit REVIEW, not invented context."""
    llm = _StructuredLLM(_valid_pm_decision())
    result = create_portfolio_manager(llm)(
        _state(
            trader_proposal=VALID_TRADER_PROPOSAL,
            portfolio=KNOWN_PORTFOLIO,
            investment_plan=None,
            trader_plan=None,
        )
    )

    assert result["guard_verdict"] == "REVIEW"
    assert result["guard_executable"] is False
    assert result["final_rating"] == "REVIEW"
    assert "unavailable" in result["final_trade_decision"].lower()
    assert llm.calls == []


def test_guarded_mode_publishes_machine_readable_guard_result():
    """INV-D6 / INV-D7 / REQ-D-007: guarded mode exposes a stable guard_result."""
    result = create_portfolio_manager(_StructuredLLM(_valid_pm_decision()))(
        _state(trader_proposal=VALID_TRADER_PROPOSAL, portfolio=KNOWN_PORTFOLIO)
    )

    guard_result = result["guard_result"]
    assert guard_result["contract"] == "validation-decision/1.1"
    assert guard_result["verdict"] in {"PASS", "BLOCK", "REVIEW"}
    assert guard_result["executable"] is (guard_result["verdict"] == "PASS")
    assert guard_result["reason_code"]
    assert guard_result["checkpoint"]
    assert guard_result["rules_hit"] == [
        {"checkpoint": "trader", "reason_code": "PASS"},
        {"checkpoint": "pm", "reason_code": "PASS"},
    ]
