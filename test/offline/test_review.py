"""Offline review contract. Fixture notes identify the requirement and invariant."""
import hashlib
import json
from pathlib import Path

import pytest

CASES = json.loads((Path(__file__).parents[1] / "fixtures/review_cases.json").read_text())


def evidence_checker(identifier):
    reasons = {"EV-1": "OK", "EV-2": "UNKNOWN_TIME", "EV-3": "FUTURE", "!": "MALFORMED"}
    return identifier == "EV-1", reasons.get(identifier, "MISSING")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case_id"])
def test_claim_validation(case):
    from tradingagents.review import validate

    earlier = dict(CASES[-1]["input"]["claims"][0], claim_id="R1", round_index=1,
                   responds_to=[], speaker="bull")
    future = dict(earlier, claim_id="R3", round_index=3)
    result = validate(case["input"]["claims"], prior_claims=[earlier, future],
                      evidence_checker=evidence_checker, statement_cap=80)
    assert result.status == case["expected_status"]
    assert result.degraded is case["expected_degraded"]
    if case["expected_violation"]:
        assert any(v.code == case["expected_violation"] and v.field and v.detail
                   and (case["expected_detail"] or "") in v.detail for v in result.violations)
    else:
        assert not result.violations


@pytest.mark.parametrize("succeeds", [False, True])
def test_repair_once(tmp_path, monkeypatch, succeeds):
    """B-REQ-05 / INV-B5: repair is bounded and preserves the raw failure."""
    from tradingagents.review import parse_with_repair

    monkeypatch.chdir(tmp_path)
    batch = {"claims": [dict(CASES[-1]["input"]["claims"][0], round_index=1, responds_to=[])]}
    raw = json.dumps(batch)[:-1]
    calls = []

    def repair(payload):
        calls.append(payload)
        return json.dumps(batch) if succeeds else raw

    result = parse_with_repair(raw, repair=repair, prior_claims=[], evidence_checker=evidence_checker,
                               output_root=tmp_path / "outputs", run_id="offline")
    assert len(calls) == result.repair_attempts == 1
    assert result.degraded is (not succeeds)
    assert result.repaired is succeeds
    if not succeeds:
        assert result.status == "degraded" and result.reason and result.raw_hash
        path = tmp_path / "outputs" / "B" / "offline" / f"repair-raw-{result.raw_hash}.txt"
        assert path.read_text() == raw
    else:
        assert result.status == "ok"
    assert set(tmp_path.iterdir()) <= {tmp_path / "outputs"}


def test_fingerprint():
    """B-REQ-09: normalize text only, with a stable 16-hex digest."""
    from tradingagents.review import fingerprint

    expected = hashlib.sha256(b"demand fell").hexdigest()[:16]
    assert fingerprint("Ｄemand   FELL!") == fingerprint("demand fell") == expected
    assert fingerprint("Orders declined") != expected


@pytest.mark.parametrize("role", ["bull", "bear"])
def test_researcher_actual_prompts(role, tmp_path):
    """B-REQ-01/02/03: capture both invocations and inject a first-round leak."""
    from importlib import import_module
    from types import SimpleNamespace

    factory = getattr(import_module(f"tradingagents.agents.researchers.{role}_researcher"),
                      f"create_{role}_researcher")
    opponent = "bear" if role == "bull" else "bull"
    other = dict(CASES[-1]["input"]["claims"][0], claim_id="prior", speaker=opponent,
                 statement="Inventories exceed the warehouse ceiling", round_index=1, responds_to=[])
    unassigned = dict(other, claim_id="secret", statement="Freight costs jumped unexpectedly")
    state = dict(run_id="fixture", instrument_context="Example company", shared_evidence=["EV-1"],
                 hard_constraints=["Respect the cutoff"], investment_debate_state={
                     "round_index": 1, "history": other["statement"], "claims": [other, unassigned]})
    import hashlib
    receipts = []
    prompts = []
    claim = dict(other, claim_id="ours", speaker=role, statement="Orders softened")

    def invoke(prompt):
        prompts.append(prompt)
        return SimpleNamespace(content=json.dumps({"claims": [claim]}))

    node = factory(SimpleNamespace(invoke=invoke), mode="collab", evidence_checker=evidence_checker,
                   output_root=tmp_path, on_prompt=receipts.append)
    first = node(state)["investment_debate_state"]
    assert first["review_status"] == "ok"
    assert other["statement"] not in prompts[0] and unassigned["statement"] not in prompts[0]
    with pytest.raises(ValueError, match="BLIND_CONTEXT_LEAK"):
        node(dict(state, market_report=other["statement"]))
    assert len(prompts) == 1
    state["investment_debate_state"] = dict(first, round_index=2)
    assert node(state)["investment_debate_state"]["review_reason"] == "NO_TARGET"
    assert len(prompts) == 1
    state["investment_debate_state"]["target_claim_ids"] = ["prior"]
    claim.update(round_index=2, responds_to=["prior"], claim_id="answer")
    second = node(state)["investment_debate_state"]
    assert second["review_status"] == "ok" and second["claims"][-1]["responds_to"] == ["prior"]
    assert other["statement"] in prompts[-1] and unassigned["statement"] not in prompts[-1]
    assert [r["input_sha256"] for r in receipts] == [hashlib.sha256(p.encode()).hexdigest() for p in prompts]
    assert receipts[0]["prompt_hashes"] == receipts[1]["prompt_hashes"]
    assert receipts[0]["input_sha256"] != receipts[1]["input_sha256"]
    claim["responds_to"] = ["secret"]
    bad = node(state)["investment_debate_state"]
    assert bad["review_status"] == "violation" and bad["claims"] == first["claims"]


@pytest.mark.parametrize("scenario", ["clear", "open", "weak", "false-resolution", "invented-reason"])
def test_manager_decision(scenario):
    """B-REQ-10: open pairs survive a false resolution and failed bounded repair."""
    from types import SimpleNamespace
    from tradingagents.agents.managers.research_manager import create_research_manager

    bull = dict(CASES[-1]["input"]["claims"][0], claim_id="B1", speaker="bull",
                round_index=1, responds_to=[], statement="Unit sales increased.")
    bear = dict(bull, claim_id="S2", speaker="bear", round_index=2, responds_to=["B1"],
                statement="Discounts reduced margin.")
    claims = [bull]
    rows = []
    if scenario in ("open", "false-resolution", "weak"):
        claims.append(bear)
        question = "Does growth offset the margin loss?"
        if scenario == "weak":
            question = "Insufficient evidence to decide between the linked claims."
        else:
            bear["unresolved_questions"] = [question]
        rows.append(dict(bull_claim_id="B1", bear_claim_id="S2", why_unresolved=question,
                         decision_impact="Requires review before a directional decision."))
    proposal = dict(adopted_claims=[dict(claim_id="B1", reason=bull["statement"])],
                    rejected_claims=[], unresolved_disagreements=rows,
                    decision_summary="REVIEW" if rows else "BUY", evidence_refs=["EV-1"])
    if scenario == "false-resolution":
        proposal.update(unresolved_disagreements=[], decision_summary="BUY")
    if scenario == "invented-reason":
        proposal["adopted_claims"][0]["reason"] = "Unreported acquisition"
    raw = json.dumps(proposal)
    calls = []

    def repair(payload):
        calls.append(payload)
        return raw

    import hashlib
    receipts, inputs = [], []
    def invoke(prompt):
        inputs.append(prompt)
        return SimpleNamespace(content=raw)
    node = create_research_manager(SimpleNamespace(invoke=invoke), on_prompt=receipts.append,
                                   mode="collab", repair=repair, evidence_checker=evidence_checker)
    state = dict(investment_debate_state=dict(claims=claims,
                 evidence_strength="weak" if scenario == "weak" else "unknown"))
    original = json.dumps(state)
    result = node(state)
    assert receipts[0]["input_sha256"] == hashlib.sha256(inputs[0].encode()).hexdigest()
    assert receipts[0]["role"] == "research_manager"
    assert json.dumps(state) == original
    plan = result["content"]
    assert plan["unresolved_disagreements"] == rows
    failed = scenario in ("false-resolution", "invented-reason")
    assert result["state_delta"]["degraded"] is failed
    assert result["state_delta"]["repair_attempts"] == len(calls) == int(failed)
    assert plan["decision_summary"] == ("REVIEW" if failed else proposal["decision_summary"])
    if failed:
        assert not plan["adopted_claims"] and result["state_delta"]["reason"]
    else:
        assert plan == proposal


def test_schema_wire_round_trip():
    """B-REQ-03/06/10/12: producer objects can be read from versioned wire data."""
    from pydantic import TypeAdapter, ValidationError
    from tradingagents.agents.schemas import Claim, ClaimBatch, ContextPack, LayerBudget, ManagerDecision, ReviewResult
    from tradingagents.context_builder import build
    from tradingagents.review import validate

    raw = dict(CASES[-1]["input"]["claims"][0], round_index=1, responds_to=[])
    review = validate([raw], prior_claims=[], evidence_checker=evidence_checker)
    context = build({"L1": [{"id": "cap", "text": "Keep the limit."}]}, 500)
    manager = ManagerDecision(adopted_claims=[], rejected_claims=[], unresolved_disagreements=[],
                              decision_summary="REVIEW", evidence_refs=[])
    for schema, obj in [(Claim, review.claims[0]), (ClaimBatch, ClaimBatch(review.claims)),
                        (ReviewResult, review), (ContextPack, context),
                        (LayerBudget, context.per_layer_tokens), (ManagerDecision, manager)]:
        adapter = TypeAdapter(schema)
        assert adapter.validate_json(adapter.dump_json(obj)) == obj
    adapter = TypeAdapter(ContextPack)
    payload = json.loads(adapter.dump_json(context))
    del payload["schema_version"]
    assert adapter.validate_python(payload).schema_version == "1.0"
    with pytest.raises(ValidationError):
        adapter.validate_python(dict(payload, schema_version="2.0"))
    with pytest.raises(ValidationError):
        TypeAdapter(LayerBudget).validate_python({"L2": -1})


def test_manager_text_boundary():
    """B-REQ-10: only validated version-one directional plans enter the text route."""
    from tradingagents.agents.managers.research_manager import render_manager_delta

    plan = dict(decision_summary="HOLD", adopted_claims=[{"claim_id":"C1","reason":"Flat orders"}],
                rejected_claims=[],unresolved_disagreements=[],evidence_refs=["news"])
    delta = dict(schema_version="1.0",degraded=False,investment_plan=plan)
    assert "C1: Flat orders" in render_manager_delta(delta)
    for version in [None, "2.0"]:
        with pytest.raises(ValueError, match="MISSING_OR_UNSUPPORTED_MANAGER_VERSION"):
            render_manager_delta(dict(delta,schema_version=version))
    with pytest.raises(ValueError, match="REVIEW_REQUIRED"):
        render_manager_delta(dict(delta,degraded=True))
    with pytest.raises(ValueError, match="REVIEW_REQUIRED"):
        render_manager_delta(dict(delta,investment_plan=dict(plan,decision_summary="REVIEW")))
