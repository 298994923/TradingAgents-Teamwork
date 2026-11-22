import json
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from tradingagents.b_interfaces import PromptReceipts, ROLES, bind_evidence
from tradingagents.review import invoke_review_prompt


def load_evidence():
    path = Path(__file__).resolve().parents[1] / "fixtures/b_evidence_v1/evidence.py"
    spec = importlib.util.spec_from_file_location("b_fixture_evidence", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_real_receipts(tmp_path):
    import hashlib
    collector = PromptReceipts("fixture")
    state = {"investment_debate_state": {"round_index": 1}}
    prompts = ["测试", "second", "third", "fourth"]
    for role, prompt in zip(["bull", "bear", "research_manager", "bull"], prompts):
        invoke_review_prompt(SimpleNamespace(invoke=str), prompt, role, state, collector.record)
    hashes = collector.finish(tmp_path, expected_calls=4)
    payload = json.loads((tmp_path / "fixture/prompt_receipts.json").read_text())
    assert set(hashes) == ROLES and payload["input_evidence"] == "完整"
    assert [r["input_sha256"] for r in payload["calls"]] == [hashlib.sha256(p.encode()).hexdigest() for p in prompts]
    assert all(r["run_id"] == "fixture" for r in payload["calls"])


def test_incomplete_and_mixed(tmp_path):
    collector = PromptReceipts("fixture")
    receipt = dict(role="bear", prompt_hashes={"b.bear": "a"*64})
    collector.record(receipt)
    for change in [dict(run_id="other"), dict(prompt_hashes={"b.bear": "b"*64}), dict(role="bull")]:
        with pytest.raises(ValueError):
            collector.record(dict(receipt, **change))
    assert collector.finish(tmp_path, expected_calls=2) == {"bear": "a"*64}
    assert json.loads((tmp_path / "fixture/prompt_receipts.json").read_text())["input_evidence"] == "输入取证不完整"


def test_actual_v1():
    evidence = load_evidence()
    fixture = json.loads(Path(evidence.__file__).with_name("evidence_cases.json").read_text())
    snapshot = evidence.register_reports(**fixture["complete"]["registration"]).snapshot
    refs = {"n": {"evidence_id": "news", "snapshot_id": snapshot.snapshot_id}}
    ordinary = bind_evidence(evidence, snapshot, refs, historical=False)
    assert bind_evidence(evidence, snapshot, refs)("n") == (False, "UNKNOWN_TIME")
    refs["n"]["snapshot_id"] = "wrong"
    assert ordinary("n") == (True, "OK")
    assert ordinary("missing") == (False, "MISSING")
    assert not bind_evidence(evidence, snapshot, refs, historical=False)("n")[0]
