"""Proposed gate-1 tests for D review. Execute explicitly before implementation."""
import pytest
from tradingagents.context_builder import build
from tradingagents.agents.managers.research_manager import create_research_manager


def test_register_bytes_and_tamper():
    from tradingagents.context_builder import HARD_CONSTRAINTS, ContextBudgetError
    items = [{"id": k, "text": v["text"]} for k, v in HARD_CONSTRAINTS.items()]
    expected = {
        "B-L1-01": "Preserve all open disagreements until explicit validated resolution.",
        "B-L1-02": "A REVIEW disposition is terminal and non-executable.",
        "B-L1-03": "The deterministic guard has final authority over executability.",
    }
    assert {k: HARD_CONSTRAINTS[k]["text"] for k in expected} == expected
    assert all(v["source"] for v in HARD_CONSTRAINTS.values())
    parts = {"L1": items, "L4": [{"id": "old", "text": "x" * 1000}]}
    pack = build(parts, 10000, compaction_threshold=0.001)
    assert pack.reinjected_constraint_ids == [i["id"] for i in items]
    assert [(b.id,b.text.encode()) for b in pack.blocks if b.layer=="L1"] == [(i["id"],i["text"].encode()) for i in items]
    items[0]["text"] += " "
    with pytest.raises(ContextBudgetError):
        build(parts, 10000)


@pytest.mark.parametrize("updates,reason", [({"context_budget":1},"CONTEXT_BUDGET_INSUFFICIENT"),
                                             ({"remaining_call_capacity":None},"CAPACITY_UNKNOWN")])
def test_no_call_when_capacity_unavailable(updates, reason, tmp_path):
    from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
    class NoCalls:
        def invoke(self, prompt):
            pytest.fail("Model invoked after terminal condition")
    node=create_bear_researcher(NoCalls(),mode="collab", evidence_checker=lambda _: (True,"OK"), output_root=tmp_path)
    result=node(dict(run_id="offline",instrument_context="Example",shared_evidence=[],
                     investment_debate_state={"round_index":1},hard_constraints=["keep"],**updates))
    assert result["stop_reason"]==reason and result["verdict"]=="REVIEW"
    assert result["executable"] is False and result["recommendation"] is None


def test_vague_impact_fails_before_call():
    class NoCalls:
        def invoke(self, prompt):
            pytest.fail("Manager invoked with unspecified decision impact")
    node=create_research_manager(NoCalls(),mode="collab",evidence_checker=lambda _: (True,"OK"))
    pair=dict(bull_claim_id="b",bear_claim_id="s",why_unresolved="Costs unknown",decision_impact="maybe")
    claims=[dict(claim_id=i,speaker=r,responds_to=[]) for i,r in [("b","bull"),("s","bear")]]
    with pytest.raises(ValueError, match="INVALID_DISAGREEMENT"):
        node({"investment_debate_state":{"claims":claims,"unresolved_disagreements":[pair]}})


@pytest.mark.parametrize("degraded", [False, True])
def test_review_handoff_is_non_executable(degraded):
    from tradingagents.agents.managers.research_manager import guard_handoff
    pair=dict(bull_claim_id="b",bear_claim_id="s",why_unresolved="Costs unknown",decision_impact="Blocks direction")
    plan=dict(decision_summary="REVIEW",adopted_claims=[],rejected_claims=[],evidence_refs=[],unresolved_disagreements=[pair])
    handoff=guard_handoff(dict(investment_plan=plan,degraded=degraded,schema_version="1.0"))
    assert handoff["verdict"]=="REVIEW" and handoff["executable"] is False
    assert handoff["recommendation"] is None and handoff["unresolved_disagreements"]==[pair]
