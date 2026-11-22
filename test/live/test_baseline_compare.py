"""S7 matched offline protocol comparison. Run as a script to emit both reports."""
import json
import math
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from time import perf_counter_ns
from types import SimpleNamespace

from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
from tradingagents.agents.researchers.bull_researcher import create_bull_researcher


class Replay:
    def __init__(self, text):
        self.text = text
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return SimpleNamespace(content=self.text)


def compare(root):
    rows = []
    observations = {}
    claim = dict(claim_id="opening", speaker="bull", statement="Inventories exceeded capacity.",
                 round_index=1, responds_to=[], evidence_ids=["E1"], unresolved_questions=[])
    for role, factory in (("bear", create_bear_researcher), ("bull", create_bull_researcher)):
        other = dict(claim, speaker="bull" if role == "bear" else "bear")
        for case, number in (("opening", 1), ("reply", 2), ("broken", 2)):
            debate = dict(history=other["statement"], current_response=other["statement"], count=1,
                          claims=[other], round_index=number, target_claim_ids=["opening"])
            state = dict(run_id=role + case, instrument_context="Fictional issuer",
                         hard_constraints=["Use dated evidence"], shared_evidence=["E1"],
                         context_budget=1024, investment_debate_state=debate)
            for source in ("market", "news", "fundamentals", "sentiment"):
                state[source + "_report"] = "No further observations."
            reply = dict(claim, claim_id="answer", speaker=role, statement="Orders were flat.",
                         round_index=number, responds_to=["opening"] if number == 2 else [])
            raw = "{" if case == "broken" else json.dumps({"claims": [reply]})
            for mode in ("legacy", "collab"):
                model = Replay(raw)
                repairs = []
                def repair(payload):
                    repairs.append(payload)
                    return raw
                options = {} if mode == "legacy" else dict(evidence_checker=lambda e: (e == "E1", "fixture"),
                                                           output_root=root / "outputs", repair=repair)
                node = factory(model, mode=mode, **options)
                trial = deepcopy(state)
                start = perf_counter_ns()
                result = node(trial)["investment_debate_state"]
                elapsed = (perf_counter_ns() - start) / 1e6
                prompt, = model.prompts
                answer = [c for c in result.get("claims", []) if c["claim_id"] == "answer"]
                rows.append(dict(role=role, case=case, round=number, mode=mode,
                                 leak=other["statement"] in prompt, linked=bool(answer and answer[0]["responds_to"] == ["opening"]),
                                 validated=result.get("review_status") == "ok",
                                 degraded=result.get("review_status") == "degraded", repairs=len(repairs),
                                 input_estimate=math.ceil(len(prompt) / 4), elapsed_ms=round(elapsed, 3)))
    bear = dict(claim, claim_id="reply", speaker="bear", responds_to=["opening"], round_index=2,
                statement="Discounts narrowed margins.", unresolved_questions=["What is the net effect?"])
    manager_state = dict(instrument_context="Fictional issuer", investment_debate_state=dict(
        count=2, claims=[claim, bear], history=claim["statement"] + " " + bear["statement"]))
    for mode in ("legacy", "collab"):
        model = Replay("Mixed evidence.")
        options = {} if mode == "legacy" else dict(evidence_checker=lambda _: (True, "fixture"))
        decision = create_research_manager(model, mode=mode, **options)(deepcopy(manager_state))
        disagreements = decision.get("content", {}).get("unresolved_disagreements", [])
        observations[mode] = [(d["bull_claim_id"], d["bear_claim_id"]) for d in disagreements]
    return rows, observations


def report(root):
    rows, managers = compare(root)
    table = []

    def row(name, values, delta, interpretation, verdict):
        table.append(dict(dimension=name, legacy=values[0], collab=values[1], delta=delta,
                          interpretation=interpretation, verdict=verdict))

    def count(case, field):
        return [sum(r[field] for r in rows if r["mode"] == m and (case is None or r["case"] == case))
                for m in ("legacy", "collab")]

    for label, case, field, expected, note in [
        ("First-round leaks / 2", "opening", "leak", [2, 0], "Both speaker orders, same opponent canary."),
        ("Valid target links / 2", "reply", "linked", [0, 2], "Counted in accepted state, not echoed text."),
        ("Validated batches / 6", None, "validated", [0, 4], "Four valid replies and two deliberately malformed replies per mode."),
        ("Explicit degradations / 2 malformed", "broken", "degraded", [0, 2], "Legacy stores malformed text. Collaboration surfaces degradation.")]:
        values = count(case, field)
        row(label, values, values[1]-values[0], note, "pass" if values == expected else "fail")
    values = [len(managers[m]) for m in ("legacy", "collab")]
    row("Open pairs retained / 1", values, values[1]-values[0], "Same invalid manager reply; tests fallback retention.",
        "pass" if managers == {"legacy": [], "collab": [("opening", "reply")]} else "fail")
    for field, label in [("input_estimate", "Estimated prompt tokens"), ("elapsed_ms", "Local researcher elapsed ms")]:
        means = [[round(sum(r[field] for r in rows if r["mode"] == m and r["case"] == case)/2, 3)
                  for case in ("opening", "reply")] for m in ("legacy", "collab")]
        row(label, means, [round(b-a, 3) for a,b in zip(*means)],
            "Opening and targeted fixture means; two speakers each. Character estimate or local wall clock, including adapter I/O.",
            ("pass" if max(r[field] for r in rows if r["mode"] == "collab") <= 1024 else "fail")
            if field == "input_estimate" else "measured")
    row("Provider input tokens and latency", ["not_run"]*2, None, "Scripted replay has no provider usage or latency.", "not_run")
    repairs = count("broken", "repairs")
    row("Repair calls / 2 malformed", repairs, repairs[1]-repairs[0], "One retry per broken collaboration response.",
        "pass" if all(r["repairs"] == (r["mode"] == "collab") for r in rows if r["case"] == "broken") else "fail")
    row("Full graph loop bound", ["not_run"]*2, None, "Independent node replays do not exercise C's scheduler.", "not_run")
    return dict(baseline_sha="9fa1196fffbcfd9de5146d2dd2869df84ab99838", model="offline scripted replay",
                temperature=None, memory="identical fresh state per paired call", rows=table, observations=rows)


def test_matched_protocol(tmp_path):
    assert all(r["verdict"] != "fail" for r in report(tmp_path)["rows"])


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as work:
        data = report(Path(work))
    destination = Path(sys.argv[1])
    destination.with_suffix(".json").write_text(json.dumps(data, indent=2) + "\n")
    fields = ["dimension", "legacy", "collab", "delta", "interpretation", "verdict"]
    lines = ["# Matched protocol comparison", "", "Each paired call uses the same synthetic ledger, reports, model reply and fresh memory. No provider connection.", "",
             "| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)]
    for r in data["rows"]:
        lines.append("| " + " | ".join(str(r[k]) if r[k] is not None else "N/A" for k in fields) + " |")
    lines += ["", "These fixtures exercise prompt isolation, reference validation and bounded fallback. They do not measure model judgment, billing, growth with debate length, or end-to-end termination.", "",
              "Reproduce from the checkout root:", "", "`PYTHONPATH=. python test/live/test_baseline_compare.py results/B/B-compare-20261120`"]
    destination.with_suffix(".md").write_text("\n".join(lines) + "\n")
