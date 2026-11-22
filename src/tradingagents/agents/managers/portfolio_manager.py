"""Portfolio Manager: synthesises the risk-analyst debate into the final decision.

Uses LangChain's ``with_structured_output`` so the LLM produces a typed
``PortfolioDecision`` directly, in a single call. Its rating is the run's
``final_rating``, and the decision is rendered to markdown as
``final_trade_decision`` for the memory log, CLI display and saved reports.
When a provider does not expose structured output, the agent falls back to
free-text generation and the rating is read from that text.

Guarded mode (``state["guard_enabled"] is True``) wires D's deterministic guard
at two checkpoints, INV-D6 / REQ-D-007:

- node start: validate ``state["trader_proposal"]`` at ``stage="trader"``;
- after the PM decision: revalidate at ``stage="pm"`` with the Trader-gate
  verdict as ``prior_verdict``.

The structured portfolio comes from ``state["portfolio"]`` only; rendered
strings are never parsed here. When the flag is absent or false, the node keeps
the upstream baseline behavior (legacy comparator), per the ADR-005
compatibility addendum.
"""

from __future__ import annotations

from tradingagents.agents.context import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_portfolio_context_from_state,
)
from tradingagents.agents.rating import parse_rating
from tradingagents.agents.schemas import PortfolioDecision, render_pm_decision
from tradingagents.agents.structured import NO_EXTERNAL_TOOLS, bind_structured, invoke_structured
from tradingagents.constraints import ABSENT, Verdict, validate as validate_guard


def _updated_risk_state(risk_debate_state):
    return {
        "history": risk_debate_state["history"],
        "aggressive_history": risk_debate_state["aggressive_history"],
        "conservative_history": risk_debate_state["conservative_history"],
        "neutral_history": risk_debate_state["neutral_history"],
        "latest_speaker": "Judge",
        "current_aggressive_response": risk_debate_state["current_aggressive_response"],
        "current_conservative_response": risk_debate_state["current_conservative_response"],
        "current_neutral_response": risk_debate_state["current_neutral_response"],
        "count": risk_debate_state["count"],
    }


def _guard_record(result):
    """Serialize one gate's GuardResult for graph/audit consumers."""
    return {
        "verdict": result.verdict.value,
        "reason_code": result.reason_code,
        "checkpoint": result.checkpoint,
        "executable": result.executable,
        "details": result.details,
    }


def _guard_fields(trader_result, pm_result, reason_code):
    return {
        "guard_verdict": pm_result.verdict.value,
        "guard_reason_code": reason_code,
        "guard_executable": pm_result.executable,
        "guard_checkpoint": pm_result.checkpoint,
        "guard_details": pm_result.details,
        "guard_trader": _guard_record(trader_result),
        "guard_pm": _guard_record(pm_result),
    }


def _guard_result_payload(trader_result, pm_result):
    """Machine-readable final safety result for the guarded run."""
    return {
        "contract": "validation-decision/1.1",
        "verdict": pm_result.verdict.value,
        "reason_code": pm_result.reason_code,
        "checkpoint": pm_result.checkpoint,
        "executable": pm_result.executable,
        "rules_hit": [
            {
                "checkpoint": trader_result.checkpoint,
                "reason_code": trader_result.reason_code,
            },
            {
                "checkpoint": pm_result.checkpoint,
                "reason_code": pm_result.reason_code,
            },
        ],
    }


def _suppressed_decision(pm_result):
    """A non-executable disposition that carries no tradeable rating or action."""
    return (
        f"GUARD {pm_result.verdict.value} ({pm_result.reason_code}): "
        "non-executable disposition; recommendation suppressed."
    )


def _unavailable_plans_result(risk_debate_state):
    """Missing research/trader plans are an explicit REVIEW, never fabricated."""
    return {
        "risk_debate_state": _updated_risk_state(risk_debate_state),
        "final_trade_decision": (
            "GUARD REVIEW (KNOWN_UNKNOWN): investment_plan or "
            "trader_investment_plan unavailable; no tradeable decision."
        ),
        "final_rating": "REVIEW",
        "guard_verdict": "REVIEW",
        "guard_reason_code": "KNOWN_UNKNOWN",
        "guard_executable": False,
        "guard_checkpoint": "pm",
        "guard_details": {
            "unavailable": ["investment_plan", "trader_investment_plan"],
        },
        "guard_trader": None,
        "guard_pm": None,
    }


def _has_plan(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def create_portfolio_manager(llm):
    structured_llm = bind_structured(llm, PortfolioDecision, "Portfolio Manager")

    def portfolio_manager_node(state) -> dict:
        instrument_context = get_instrument_context_from_state(state)
        portfolio_context = get_portfolio_context_from_state(state)

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        guard_enabled = state.get("guard_enabled") is True

        if guard_enabled:
            raw_research_plan = state.get("investment_plan")
            raw_trader_plan = state.get("trader_investment_plan")
            if not _has_plan(raw_research_plan) or not _has_plan(raw_trader_plan):
                return _unavailable_plans_result(risk_debate_state)
            research_plan = raw_research_plan
            trader_plan = raw_trader_plan

            raw_portfolio = state.get("portfolio", ABSENT)
            guard_portfolio = raw_portfolio if isinstance(raw_portfolio, dict) else ABSENT
            raw_trader_proposal = state.get("trader_proposal")
            trader_proposal = (
                raw_trader_proposal if isinstance(raw_trader_proposal, dict) else {}
            )

            # INV-D6: Trader gate runs before the PM prompt/decision.
            trader_result = validate_guard(
                proposal=trader_proposal,
                portfolio=guard_portfolio,
                stage="trader",
            )
        else:
            research_plan = state["investment_plan"]
            trader_plan = state["trader_investment_plan"]

        past_context = state.get("past_context", "")
        lessons_line = (
            f"- Lessons from prior decisions and outcomes:\n{past_context}\n"
            if past_context
            else ""
        )

        prompt = f"""As the Portfolio Manager, synthesize the risk analysts' debate and deliver the final trading decision.

{instrument_context}

{portfolio_context}

---

**Rating Scale** (use exactly one):
- **Buy**: Strong conviction to enter or add to position
- **Overweight**: Favorable outlook, gradually increase exposure
- **Hold**: Maintain current position, no action needed
- **Underweight**: Reduce exposure, take partial profits
- **Sell**: Exit position or avoid entry

**Context:**
- Research Manager's investment plan: **{research_plan}**
- Trader's transaction proposal: **{trader_plan}**
{lessons_line}
**Risk Analysts Debate History:**
{history}

---

Ground every conclusion in specific evidence from the analysts. The risk debate always contains conflicting stances; deciding which is stronger is the job, so conflict alone is not a reason to Hold. Commit to the stronger case, sized by how decisively it wins. Choose Hold only when the evidence is still balanced after that weighing, or too thin to support a call; do not force a direction to appear decisive. Weigh the analysts on their merits, independent of speaking order.

## Output

Write these sections, in this order, starting with the rating on its own line:

- **Rating**: exactly one of Buy / Overweight / Hold / Underweight / Sell
- **Executive Summary**: the call and how to act on it
- **Investment Thesis**: the evidence that decided it, and what would change it

{NO_EXTERNAL_TOOLS}{get_language_instruction()}"""

        # The typed rating is the decision; the rendered text only carries it.
        # Read back from text, a rating the thesis quotes could replace it.
        decision = invoke_structured(structured_llm, prompt, "Portfolio Manager")
        if decision is not None:
            final_trade_decision = render_pm_decision(decision)
            final_rating = decision.rating.value
        else:
            final_trade_decision = llm.invoke(prompt).content
            final_rating = parse_rating(final_trade_decision)

        new_risk_debate_state = _updated_risk_state(risk_debate_state)

        if not guard_enabled:
            return {
                "risk_debate_state": new_risk_debate_state,
                "final_trade_decision": final_trade_decision,
                "final_rating": final_rating,
            }

        # INV-D6 / INV-D7: final gate revalidates the PM output and preserves
        # any higher prior verdict. PM text is passed only for override audit.
        pm_proposal = dict(trader_proposal)
        pm_proposal["rating"] = final_rating
        pm_result = validate_guard(
            proposal=pm_proposal,
            portfolio=guard_portfolio,
            stage="pm",
            prior_verdict=trader_result.verdict,
            llm_text=final_trade_decision,
        )

        reason_code = pm_result.reason_code
        if (
            pm_result.verdict == Verdict.REVIEW
            and trader_result.verdict == Verdict.REVIEW
            and pm_result.reason_code == "REVIEW_TERMINAL"
        ):
            # A carried-forward REVIEW keeps its originating reason in the
            # top-level field; both gate records remain available.
            reason_code = trader_result.reason_code

        if pm_result.verdict != Verdict.PASS:
            final_trade_decision = _suppressed_decision(pm_result)
            final_rating = "REVIEW"

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": final_trade_decision,
            "final_rating": final_rating,
            "guard_result": _guard_result_payload(trader_result, pm_result),
            **_guard_fields(trader_result, pm_result, reason_code),
        }

    return portfolio_manager_node
