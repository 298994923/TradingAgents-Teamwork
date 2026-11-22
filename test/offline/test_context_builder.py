"""Deterministic context tests with no provider SDK or network calls."""
import hashlib

import pytest


def parts():
    return {layer: [{"id": layer, "text": text}] for layer, text in zip(
        ("L0", "L1", "L2", "L3", "L4", "L5"), ("bull", "hold", "data", "task", "past", "none")
    )}


def test_blind_round_and_reverse_control():
    """B-REQ-01 / INV-B1: detect leakage even when the opponent spoke first."""
    from tradingagents.context_builder import build_blind_prompt, assert_blind
    from tradingagents.review import fingerprint

    for speaker, opponent in [("bull", "bear"), ("bear", "bull")]:
        text = f"Unique {opponent} claim about inventories"
        claim = {"speaker": opponent, "statement": text, "claim_id": "R1", "round_index": 1}
        prompt = build_blind_prompt(parts(), speaker=speaker, prior_claims=[claim])
        assert text.casefold() not in prompt.casefold()
        assert fingerprint(text) not in prompt
        assert_blind(prompt, opponent_claims=[claim])
        with pytest.raises(ValueError):
            assert_blind(prompt + "\n" + text, opponent_claims=[claim])


def test_impossible_budget():
    """B-REQ-07/08 / INV-B4: never truncate hard constraints."""
    from tradingagents.context_builder import build, ContextBudgetError

    with pytest.raises(ContextBudgetError):
        build(parts(), 1, estimator=len)


def test_budget_boundary_and_compaction():
    """B-REQ-06/07/08 / INV-B4/B6: exact limit, one over, and L1 identity."""
    from tradingagents.context_builder import build

    items = parts()
    items["L1"].append({"id": "second", "text": "Keep CASH!"})

    def assemble(budget):
        return build(items, budget, estimator=len, compaction_threshold=1.0)

    full = assemble(10000)
    exact = assemble(full.estimated_tokens)
    assert not exact.compaction_triggered
    assert [block.layer for block in exact.blocks] == ["L0", "L1", "L1", "L2", "L3", "L4", "L5"]
    compact = assemble(full.estimated_tokens - 1)
    assert compact.compaction_triggered and compact.estimated_tokens <= compact.budget
    assert compact.dropped and all(d.id in {"L2", "L4"} and d.reason for d in compact.dropped)

    def constraints(pack):
        return [(b.id, hashlib.sha256(b.text.encode()).hexdigest()) for b in pack.blocks if b.layer == "L1"]

    assert constraints(compact) == constraints(full)
    assert set(compact.reinjected_constraint_ids) == {"L1", "second"}


def test_context_dedup():
    """B-REQ-09: retain different wording and record the first duplicate's ID."""
    from tradingagents.context_builder import build

    items = parts()
    items["L2"] += [{"id": "dup", "text": "DATA!"}, {"id": "distinct", "text": "information"}]
    pack = build(items, 10000, estimator=len)
    assert {b.id for b in pack.blocks if b.layer == "L2"} == {"L2", "distinct"}
    assert any(d.id == "dup" and d.duplicate_of == "L2" for d in pack.dropped)


def test_metrics_and_placement(tmp_path, monkeypatch):
    """B-REQ-12: signed input-token error and separate snapshot and result paths."""
    from tradingagents.context_builder import build, write_context_artifacts

    monkeypatch.chdir(tmp_path)
    empty = build(parts(), 10000, estimator=len)
    assert empty.actual_tokens is None and empty.estimation_error is None
    assert "actual usage unavailable" in empty.warnings
    pack = build(parts(), 10000, estimator=len, actual_usage={"input_tokens": 101})
    assert pack.actual_tokens == 101
    assert pack.estimation_error == pack.estimated_tokens - 101
    write_context_artifacts(pack, root=tmp_path, run_id="offline", round_index=1)
    assert list((tmp_path / "outputs/B/offline").glob("context-r1-*.json"))
    assert (tmp_path / "results/B/context-metrics.json").is_file()
    assert not (tmp_path / "results/metrics.json").exists()
    assert set(tmp_path.iterdir()) == {tmp_path / "outputs", tmp_path / "results"}
