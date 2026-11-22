"""S9 opt-in live evaluation. Run as a script; ordinary test collection is offline."""
import hashlib
import json
import os
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from openai import OpenAI, APIConnectionError, APIStatusError
from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
from tradingagents import __version__
from tradingagents.review import _recover, prompt_hashes
from tradingagents.run_recorder import RunEvent, build_run_id, write_manifest

MODEL = "CS5351/DeepSeek-V4-Flash"
CANARY = "The fictional issuer doubled overnight warehouse capacity."
QUESTION = "Can unit growth offset the gross margin decline?"
CONSTRAINT = "Use only observations available on the fixture date."
EVIDENCE = [{"id": "EV-1", "text": "Unit sales increased 8 percent."},
            {"id": "EV-2", "text": "Gross margin declined two percentage points."}]
CASES = ("blind", "target-full", "target-compact", "manager")
METRICS = {"first_round_leakage": 0, "target_hit": 1, "valid_evidence": 1,
           "constraint_retention": 1, "disagreement_retention": 1,
           "structural_validity": 1, "repair_success": 1}


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n")


def fixture(case, run):
    bull = dict(claim_id="B1", speaker="bull", statement=CANARY, round_index=1,
                responds_to=[], evidence_ids=["EV-1"], unresolved_questions=[])
    own = dict(bull, claim_id="S1", speaker="bear", statement="Historical note on margin.")
    pair = dict(bull_claim_id="B1", bear_claim_id="S1", why_unresolved=QUESTION,
                decision_impact="Requires review before a directional decision.")
    return dict(run_id=run, instrument_context="Fictional issuer ACME",
                hard_constraints=[CONSTRAINT], shared_evidence=EVIDENCE,
                context_budget=4096, compaction_threshold=0.01 if case == "target-compact" else 1.0,
                investment_debate_state=dict(claims=[bull, own], count=0, round_index=1 if case=="blind" else 2,
                    target_claim_ids=["B1"], unresolved_disagreements=[pair], unresolved_questions=[QUESTION]))


def evaluate(case, rep, root, client, start):
    run = build_run_id("s9-"+case, "ACME", "2026-11-20", rep, start)
    directory = root / run
    directory.mkdir()
    row = dict(case=case, repetition=rep, run_id=run, metrics={}, malformed=0, fabricated=0)
    trial_started = time.perf_counter()
    calls = []
    state = fixture(case, run)

    def invoke(prompt):
        write(directory / "prompt.json", prompt)
        started = time.perf_counter()
        reply = client.chat.completions.create(model=MODEL, messages=[dict(role="user", content=prompt)],
                                               temperature=0, max_tokens=2048)
        seconds = time.perf_counter() - started
        content = reply.choices[0].message.content or ""
        write(directory / "response.json", content)
        calls.append((prompt, reply.usage, seconds))
        usage = {"input_tokens": reply.usage.prompt_tokens} if reply.usage else {}
        return SimpleNamespace(content=content, usage_metadata=usage)

    def checker(key):
        return key in ("EV-1", "EV-2"), "MISSING" if re.fullmatch(r"EV-\d+", key) else "MALFORMED"

    options = dict(mode="collab", evidence_checker=checker, repair=lambda raw: json.dumps(_recover(raw)))
    try:
        model = SimpleNamespace(invoke=invoke)
        if case == "manager":
            result = create_research_manager(model, **options)(state)
            delta = result["state_delta"]
            row["metrics"]["disagreement_retention"] = [int(result["content"]["unresolved_disagreements"]
                == state["investment_debate_state"]["unresolved_disagreements"])]
            row["metrics"]["structural_validity"] = [int(not delta["degraded"])]
            attempts, success = delta["repair_attempts"], not delta["degraded"]
        else:
            node = create_bear_researcher(model, output_root=directory/"outputs", **options)
            delta = node(state)["investment_debate_state"]
            review = delta["review_result"]
            success = review["status"] == "ok"
            attempts = review["repair_attempts"]
            row["metrics"]["structural_validity"] = [int(success)]
            if case == "blind":
                row["metrics"]["first_round_leakage"] = [int(CANARY in calls[0][0])]
            else:
                row["metrics"]["target_hit"] = [int(success and all(c["responds_to"] == ["B1"] for c in review["claims"]))]
            try:
                raw_claims = json.loads((directory/"response.json").read_text())
                parsed = json.loads(raw_claims)["claims"]
                refs = [r for c in parsed for r in c["evidence_ids"]]
                row["metrics"]["valid_evidence"] = [int(r in ("EV-1","EV-2")) for r in refs]
                for r in refs:
                    if r not in ("EV-1","EV-2"):
                        row["fabricated" if isinstance(r,str) and re.fullmatch(r"EV-\d+",r) else "malformed"] += 1
            except (KeyError, TypeError, ValueError):
                pass
            phase = "compacted" if case == "target-compact" else "assembled"
            pack = json.loads((directory/f"outputs/B/{run}/bear-context-r{state['investment_debate_state']['round_index']}-{phase}.json").read_text())
            row["estimated"] = pack["estimated_tokens"]
            if case == "target-compact":
                row["metrics"]["constraint_retention"] = [int(pack["compaction_triggered"] and
                    [b["text"] for b in pack["blocks"] if b["layer"]=="L1"] == [CONSTRAINT])]
        row["repair_attempted"] = bool(attempts)
        row["repair_attempts"] = attempts
        if attempts:
            row["metrics"]["repair_success"] = [int(success)]
        write(directory/"observed.json",delta)
    except (APIConnectionError, APIStatusError) as exc:
        row["error"] = f"{type(exc).__name__}: {getattr(exc,'status_code','')} {str(exc)[:400]}"
    if calls:
        _, usage, seconds = calls[0]
        role = "research_manager" if case == "manager" else "bear"
        duration = time.perf_counter() - trial_started
        stats = dict(llm_calls=1, tool_calls=0, tokens_in=usage.prompt_tokens if usage else None,
                     tokens_out=usage.completion_tokens if usage else None)
        event = RunEvent(run_id=run, created_at=start.isoformat(), version=__version__, ticker="ACME",
                         trade_date="2026-11-20", asset_type="stock", outcome=None,
                         config_snapshot={"model": MODEL, "temperature": 0}, prompt_hashes=prompt_hashes(role),
                         evidence_snapshot=None, usage=stats, duration_seconds=duration, failure=None, stop_reason=None)
        path = write_manifest(event, directory/"manifest.json")
        row.update(source_run_id=None, usage_complete=usage is not None, trial_duration_s=duration)
        row["manifest_path"] = str(path.relative_to(root))
        row["manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        actual = json.loads(path.read_text())
        row.update(actual_input=actual["usage"]["tokens_in"] if usage else None,
                   actual_output=actual["usage"]["tokens_out"] if usage else None,
                   seconds=seconds)
    return row


def publish(result, dest):
    rows = result["observations"]
    lines = ["# S9 fixed-set evaluation", "", f"Model: {MODEL}. Three fresh repetitions per case. "
             "Temperature 0; seed unspecified. Record-level provenance and hashes are in the companion JSON.",
             "", "| Metric | Samples | Passes | Rate | Repeat mean | Range width | Threshold | Met |",
             "|---|---:|---:|---:|---:|---:|---:|---|"]
    for name, metric in result["metrics"].items():
        values = [metric[k] for k in ("samples","passes","rate","mean","spread","threshold","met")]
        lines.append("| " + " | ".join([name, *["not_run" if v is None else str(round(v,4)) if type(v) is float else str(v) for v in values]]) + " |")
    lines += ["", "Rates count leaks per captured opening, exact assigned links per targeted response, valid IDs per parseable raw citation, retained L1 text per compacted pack, retained pairs per manager output (including fallback), accepted final structures per response, and successful repairs per attempted repair. Spread is max minus min across available repetition rates. Zero attempts produce no repair score.",
              "", "| Case / repeat | Actual input (metrics.json) | Estimated input | Error (estimate - actual) | Actual output | Elapsed seconds |",
              "|---|---:|---:|---:|---:|---:|"]
    for r in rows:
        actual = r.get("actual_input")
        est = r.get("estimated")
        values = [actual,est,est-actual if est is not None and actual is not None else None,r.get("actual_output"),r.get("seconds")]
        lines.append("| " + " | ".join([f"{r['case']} / {r['repetition']}", *[str(v) if v is not None else "not_run" for v in values]]) + " |")
    errors = [r["estimated"]-r["actual_input"] for r in rows if r.get("actual_input") is not None and "estimated" in r]
    pairs = []
    for rep in (1,2,3):
        by_case = {r["case"]:r for r in rows if r["repetition"]==rep}
        a,b = by_case["target-full"],by_case["target-compact"]
        if a.get("actual_input") is not None and b.get("actual_input") is not None:
            pairs.append(b["actual_input"]-a["actual_input"])
    lines += ["", f"Matched compact-minus-full input-token deltas: {pairs or 'not_run'}. "
              f"Observed estimator error band: {str((min(errors),max(errors))) if errors else 'not_run'}.",
              f"Fabricated references: {sum(r['fabricated'] for r in rows)}; malformed references: {sum(r['malformed'] for r in rows)} (parseable outputs only).",
              "", "A manifest covers one isolated model call, timed around the provider request, not a production graph round. The team manifest writer ran in each isolated trial directory. Manager prompts bypass the B context estimator.",
              "", "The S8 team snapshot contains no docs/evaluation/protocol.md. These results follow the B brief and await E's protocol reconciliation. Target hits measure accepted links, not the persuasiveness of an argument. Thresholds apply only to this fixed set.",
              "", "Prompt v1.1: insufficient evidence for adopting a new version; no candidate v1.1 was compared. Inspect failures and test a candidate on the same inputs before changing versions."]
    failures = [r for r in rows if r.get("error")]
    if failures:
        lines += ["", f"Unavailable provider trials: {len(failures)}/{len(rows)}. First error: {failures[0]['error']}. Missing trials cannot clear gate 4."]
    if any(m["met"] is False for m in result["metrics"].values()):
        lines += ["", "Threshold misses remain open. Inspect the raw responses for JSON formatting, citation/link errors and manager validation reasons, then rerun unchanged cases after identifying a specific fix."]
    body = "\n".join(lines) + "\n"
    dest.with_suffix(".md").write_text(body)
    Path("docs/plans/B-09-eval-report.md").write_text(body + "\nReproduce from the checkout root: "
        "`PYTHONPATH=src python test/live/test_review_quality.py`\n")


def main():
    cfg = json.loads((Path.home()/".config/opencode/opencode.json").read_text())["provider"]["cityu"]["options"]
    if cfg["baseURL"].rstrip("/") != "https://llm.cs.cityu.edu.hk/v1":
        raise ValueError("Unexpected CityU endpoint")
    client = OpenAI(api_key=cfg["apiKey"],base_url=cfg["baseURL"],timeout=60,max_retries=0)
    start = datetime.now(timezone.utc)
    root = Path("outputs/B") / start.strftime("s9-%Y%m%dT%H%M%S%fZ")
    root.mkdir(parents=True)
    jobs = [(case, rep) for rep in range(1,4) for case in CASES]
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda j:evaluate(*j,root,client,start),jobs))
    metrics = {}
    for name, threshold in METRICS.items():
        groups = [[v for r in rows if r["repetition"]==rep for v in r["metrics"].get(name,[])] for rep in (1,2,3)]
        rates = [statistics.mean(g) for g in groups if g]
        vals = sum(groups,[])
        passed = sum(v == threshold for v in vals)
        metrics[name] = dict(samples=len(vals),passes=passed,rate=statistics.mean(vals) if vals else None,
                             mean=statistics.mean(rates) if rates else None,spread=max(rates)-min(rates) if rates else None,
                             threshold=threshold,met=(passed==len(vals) and len(rates)==3) if vals else None)
    result = dict(timestamp=start.isoformat(),model=MODEL,temperature=0,seed=None,memory="fresh fixture each call",
                  prompt_version="1.0",prompt_sha256=hashlib.sha256(Path("prompts/prompt_v1.0.yaml").read_bytes()).hexdigest(),
                  case_sha256=hashlib.sha256(json.dumps([fixture(c,"fixed") for c in CASES],sort_keys=True).encode()).hexdigest(),
                  run_id=root.name,metrics=metrics,observations=rows)
    dest=Path("results/B") / ("B-09-eval-"+start.astimezone().date().isoformat())
    dest.parent.mkdir(parents=True,exist_ok=True)
    write(dest.with_suffix(".json"),result)
    publish(result, dest)
    print(dest, json.dumps(metrics), [r.get("error") for r in rows if r.get("error")][:1])


if __name__=="__main__":
    main()


def test_trial_manifest_interop(tmp_path):
    """B-REQ-12: verify a real team manifest using an offline provider response."""
    from tradingagents.run_recorder import read_manifest
    from tradingagents.context_builder import build, write_context_artifacts

    def complete(**kwargs):
        claim = dict(claim_id="S2", speaker="bear", statement="Margin declined.", evidence_ids=["EV-2"],
                     responds_to=[], unresolved_questions=[], round_index=1)
        message = SimpleNamespace(content=json.dumps({"claims": [claim]}))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)],
                               usage=SimpleNamespace(prompt_tokens=123, completion_tokens=32))

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete)))
    at = datetime(2026,11,21,12,tzinfo=timezone.utc)
    row = evaluate("blind", 1, tmp_path, client, at)
    event = read_manifest(tmp_path/row["manifest_path"])
    assert event["prompt_hashes"] == prompt_hashes("bear")
    assert event["run_id"] == row["run_id"] and row["source_run_id"] is None
    assert row["actual_input"] == 123 and row["repair_attempted"] is False
    dotted = build_run_id("v2","BRK.B","2026-11-20",1,at)
    write_context_artifacts(build({},500),root=tmp_path,run_id=dotted,round_index=1)
    assert (tmp_path/"outputs/B"/dotted).is_dir()
