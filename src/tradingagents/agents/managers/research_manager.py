"""Research Manager: turns the bull/bear debate into a structured investment plan for the trader."""

from __future__ import annotations

from tradingagents.agents.context import get_instrument_context_from_state, get_language_instruction
from tradingagents.agents.schemas import ResearchPlan, render_research_plan
from tradingagents.agents.structured import (
    NO_EXTERNAL_TOOLS,
    bind_structured,
    invoke_structured_or_freetext,
)


def create_research_manager(llm, mode="legacy", **options):
    if mode == "collab":
        return _collab_manager(llm, **options)
    if mode != "legacy" or options:
        raise ValueError("Unsupported manager configuration")
    structured_llm = bind_structured(llm, ResearchPlan, "Research Manager")

    def research_manager_node(state) -> dict:
        instrument_context = get_instrument_context_from_state(state)
        history = state["investment_debate_state"].get("history", "")

        investment_debate_state = state["investment_debate_state"]

        prompt = f"""As the Research Manager and debate facilitator, your role is to critically evaluate this round of debate and deliver a clear, actionable investment plan for the trader.

{instrument_context}

---

**Rating Scale** (use exactly one):
- **Buy**: Strong conviction in the bull thesis; recommend taking or growing the position
- **Overweight**: Constructive view; recommend gradually increasing exposure
- **Hold**: Balanced view; recommend maintaining the current position
- **Underweight**: Cautious view; recommend trimming exposure
- **Sell**: Strong conviction in the bear thesis; recommend exiting or avoiding the position

The debate always contains conflicting arguments; deciding which side is stronger is the job, so conflict alone is not a reason to Hold. Commit to the side with the stronger case, sized by how decisively it wins. Choose Hold only when the evidence is still balanced after that weighing, or too thin to support a call; do not manufacture a direction to appear decisive. Weigh the bull and bear cases on their merits, independent of which side spoke first or last.

---

**Debate History:**
{history}

## Output

Write these sections, in this order, starting with the recommendation on its own line:

- **Recommendation**: exactly one of Buy / Overweight / Hold / Underweight / Sell
- **Rationale**: which arguments decided it
- **Strategic Actions**: concrete steps for the trader, sized against a standard allocation

{NO_EXTERNAL_TOOLS}""" + get_language_instruction()

        investment_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_research_plan,
            "Research Manager",
        )

        new_investment_debate_state = {
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": investment_plan,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": investment_plan,
        }

    return research_manager_node


def _open_items(debate, ledger):
    """Carry explicit open pairs and recover open questions linked by a targeted reply."""
    rows = list(debate.get("unresolved_disagreements", []))
    questions = list(debate.get("unresolved_questions", []))
    for claim in ledger.values():
        questions.extend(claim.get("unresolved_questions", []))
        for target in claim["responds_to"]:
            prior = ledger[target]
            if claim["speaker"] == prior["speaker"]:
                raise ValueError("INVALID_TARGET")
            bull, bear = (claim, prior) if claim["speaker"] == "bull" else (prior, claim)
            linked = list(dict.fromkeys([*claim.get("unresolved_questions", []),
                                        *prior.get("unresolved_questions", [])]))
            if not linked and debate.get("evidence_strength") == "weak":
                linked = ["Insufficient evidence to decide between the linked claims."]
            for question in linked:
                if not any(r["bull_claim_id"] == bull["claim_id"] and r["bear_claim_id"] == bear["claim_id"]
                           and r["why_unresolved"] == question for r in rows):
                    rows.append(dict(bull_claim_id=bull["claim_id"], bear_claim_id=bear["claim_id"],
                                     why_unresolved=question, decision_impact="Requires review before a directional decision."))
    for row in rows:
        if (ledger[row["bull_claim_id"]]["speaker"] != "bull" or
                ledger[row["bear_claim_id"]]["speaker"] != "bear" or
                not row["why_unresolved"] or not row["decision_impact"]):
            raise ValueError("INVALID_DISAGREEMENT")
    return rows, list(dict.fromkeys(questions))


def _collab_manager(llm, *, evidence_checker, repair=None, on_prompt=None):
    import json
    from tradingagents.agents.schemas import ManagerDecision

    from tradingagents.review import MAX_REPAIR_ATTEMPTS, invoke_review_prompt, researcher_prompt, validate_manager_refs

    def node(state):
        debate = state["investment_debate_state"]
        claims = debate["claims"]
        ledger = {c["claim_id"]: c for c in claims}
        if len(ledger) != len(claims):
            raise ValueError("DUP_ID")
        open_rows, questions = _open_items(debate, ledger)
        template = dict(adopted_claims=[], rejected_claims=[], unresolved_disagreements=open_rows,
                        decision_summary="REVIEW", evidence_refs=[])
        context = dict(claims=claims, unresolved_disagreements=open_rows, unresolved_questions=questions)
        prompt = researcher_prompt("research_manager") + json.dumps(context, ensure_ascii=False)
        raw = invoke_review_prompt(llm, prompt, "research_manager", state, on_prompt).content
        reason = None
        attempts = 0
        plan = template
        while True:
            try:
                candidate = json.loads(raw)
                if not isinstance(candidate, dict) or set(candidate) != set(template):
                    raise ValueError("INVALID_MANAGER_FIELDS")
                for name in ("adopted_claims", "rejected_claims", "unresolved_disagreements", "evidence_refs"):
                    if not isinstance(candidate[name], list):
                        raise ValueError("INVALID_MANAGER_LIST")
                for item in candidate["adopted_claims"] + candidate["rejected_claims"]:
                    if set(item) != {"claim_id", "reason"} or not item["reason"]:
                        raise ValueError("INVALID_DISPOSITION")
                validate_manager_refs(candidate["adopted_claims"], candidate["rejected_claims"],
                                      candidate["evidence_refs"], ledger, evidence_checker)
                if candidate["unresolved_disagreements"] != open_rows:
                    raise ValueError("DISAGREEMENT_CHANGED")
                summary = candidate["decision_summary"]
                if summary not in ("BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL", "REVIEW"):
                    raise ValueError("INVALID_SUMMARY")
                if summary != "REVIEW" and (open_rows or questions or not candidate["adopted_claims"]
                                            or debate.get("evidence_strength") == "weak"):
                    raise ValueError("REVIEW_REQUIRED")
                plan = ManagerDecision.model_validate(candidate).model_dump()
                reason = None
                break
            except (ValueError, KeyError, TypeError) as exc:
                reason = str(exc) if isinstance(exc, ValueError) else "INVALID_MANAGER_OUTPUT"
            if repair is None or attempts >= MAX_REPAIR_ATTEMPTS:
                break
            attempts += 1
            try:
                raw = repair(raw)
            except Exception:
                reason = "REPAIR_FAILED"
                break
        return {"content": plan, "state_delta": {"schema_version": "1.0", "investment_plan": plan,
                "unresolved_questions": questions, "degraded": reason is not None,
                "reason": reason, "repair_attempts": attempts}}

    return node


def render_manager_delta(delta):
    """Render a checked collaboration delta for C's string-only trader handoff."""
    from tradingagents.agents.schemas import ManagerDecision

    if delta.get("schema_version") != "1.0":
        raise ValueError("MISSING_OR_UNSUPPORTED_MANAGER_VERSION")
    plan = ManagerDecision.model_validate(delta["investment_plan"])
    if type(delta.get("degraded")) is not bool:
        raise ValueError("INVALID_MANAGER_DELTA")
    if delta["degraded"] or plan.decision_summary == "REVIEW" or plan.unresolved_disagreements:
        raise ValueError("REVIEW_REQUIRED")
    if not plan.adopted_claims:
        raise ValueError("MISSING_ADOPTED_CLAIMS")
    reasons = [f"{c.claim_id}: {c.reason}" for c in plan.adopted_claims]
    return "\n".join([plan.decision_summary, *reasons, "Evidence: " + ", ".join(plan.evidence_refs)])
