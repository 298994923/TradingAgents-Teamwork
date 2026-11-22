"""Ordered debate context. Character-based estimates are not provider billing."""
import hashlib
import json
import math
import os
from tradingagents.run_recorder import RUN_ID_PATTERN
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Annotated, Literal

from pydantic import Field

from tradingagents.review import _visible_text, fingerprint

LAYERS = ("L0", "L1", "L2", "L3", "L4", "L5")
DEFAULT_THRESHOLD = 0.85


class ContextBudgetError(ValueError):
    """The required context cannot be emitted intact."""


@dataclass
class Block:
    layer: str
    id: str
    text: str
    metadata: dict = field(default_factory=dict)

    def render(self):
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":")) + "\n"


@dataclass
class Dropped:
    id: str
    reason: str
    duplicate_of: str | None = None


LayerName = Literal["L0", "L1", "L2", "L3", "L4", "L5"]
LayerBudget = dict[LayerName, Annotated[int, Field(ge=0)]]


@dataclass
class ContextPack:
    blocks: list[Block]
    budget: int
    per_layer_tokens: LayerBudget
    total_tokens: int
    estimated_tokens: int
    actual_tokens: int | None
    estimation_error: int | None
    compaction_triggered: bool
    reinjected_constraint_ids: list[str]
    dropped: list[Dropped]
    warnings: list[str]
    elapsed_ms: float
    version: Literal["1.0"] = "1.0"
    schema_version: Literal["1.0"] = "1.0"

    def render(self):
        return "".join(block.render() for block in self.blocks)


def _estimate(text):
    return math.ceil(len(text) / 4)


def _identity(block):
    return block.id, hashlib.sha256(block.text.encode()).hexdigest()


def build(parts, budget, *, estimator=None, actual_usage=None, compaction_threshold=DEFAULT_THRESHOLD):
    started = perf_counter()
    if type(budget) is not int or budget < 1 or not 0 < compaction_threshold <= 1:
        raise ValueError("Invalid budget or compaction threshold")
    if set(parts) - set(LAYERS):
        raise ValueError("Unknown context layer")
    estimate = estimator or _estimate
    blocks, dropped = [], []
    for layer in LAYERS:
        entries = parts.get(layer, [])
        if layer == "L5" and not entries:
            entries = [{"id": "resume", "text": "unknown"}]
        seen = {}
        for item in entries:
            identifier, text = item["id"], item["text"]
            if not isinstance(identifier, str) or not identifier or not isinstance(text, str):
                raise ValueError("Invalid context block")
            meta = {k: v for k, v in item.items() if k not in ("id", "text")}
            key = (fingerprint(text), meta.get("speaker"))
            if layer in ("L2", "L4") and key in seen:
                dropped.append(Dropped(identifier, "duplicate", seen[key]))
                continue
            seen[key] = identifier
            blocks.append(Block(layer, identifier, text, meta))

    protected = [b for b in blocks if b.layer in ("L0", "L1")]
    original = [_identity(b) for b in protected]
    costs = {id(b): estimate(b.render()) for b in blocks}
    if any(type(cost) is not int or cost < 0 for cost in costs.values()):
        raise ValueError("Estimator must return nonnegative integer costs")
    total = sum(costs.values())
    compact = total > budget * compaction_threshold
    removed = set()
    if compact:
        def priority(b):
            meta = b.metadata
            if b.layer == "L4":
                return (0, bool(meta.get("unresolved") or meta.get("disagreement")),
                        meta.get("citation_count", 0))
            if b.layer == "L5":
                return (1,)
            return (2, meta.get("tier", 0), meta.get("timestamp") or "", meta.get("citation_count", 0))

        candidates = sorted((b for b in blocks if b.layer in ("L4", "L5", "L2")), key=priority)
        for b in candidates:
            routine = b.layer == "L4" and not any(b.metadata.get(k) for k in
                                                  ("unresolved", "disagreement", "citation_count"))
            if total <= budget and not routine:
                continue
            removed.add(id(b))
            total -= costs[id(b)]
            dropped.append(Dropped(b.id, "routine history" if routine else "budget"))
        blocks = protected + [b for b in blocks if b.layer not in ("L0", "L1") and id(b) not in removed]
    if total > budget or original != [_identity(b) for b in blocks if b.layer in ("L0", "L1")]:
        raise ContextBudgetError("Required context exceeds budget or protected text changed")
    totals = dict.fromkeys(LAYERS, 0)
    for b in blocks:
        totals[b.layer] += costs[id(b)]
    actual = None if actual_usage is None else actual_usage.get("input_tokens")
    if actual is not None and (type(actual) is not int or actual < 0):
        raise ValueError("Invalid input token usage")
    return ContextPack(blocks, budget, totals, total, total, actual,
                       None if actual is None else total - actual, compact,
                       [b.id for b in protected if b.layer == "L1"] if compact else [], dropped,
                       ["actual usage unavailable"] if actual is None else [],
                       (perf_counter() - started) * 1000)


def assert_blind(prompt, *, opponent_claims):
    visible = _visible_text(prompt)
    for claim in opponent_claims:
        text = claim["statement"]
        normalized = _visible_text(text)
        if (normalized and normalized in visible) or fingerprint(text) in visible:
            raise ValueError("BLIND_CONTEXT_LEAK")


def build_blind_prompt(parts, *, speaker, prior_claims):
    safe = {k: parts.get(k, []) for k in LAYERS[:4]}
    prompt = build(safe, 2**31).render()
    assert_blind(prompt, opponent_claims=[c for c in prior_claims if c["speaker"] != speaker])
    return prompt


def _write(path, value):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        try:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush()
            os.replace(f.name, path)
        finally:
            Path(f.name).unlink(missing_ok=True)


def write_context_artifacts(pack, *, root, run_id, round_index, speaker=None):
    import fcntl

    if not RUN_ID_PATTERN.fullmatch(run_id) or type(round_index) is not int or round_index < 1:
        raise ValueError("Invalid run or round")
    if speaker not in (None, "bull", "bear"):
        raise ValueError("Invalid speaker")
    raw = Path(root) / "outputs/B" / run_id
    results = Path(root) / "results/B"
    raw.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    suffix = "compacted" if pack.compaction_triggered else "assembled"
    prefix = f"{speaker}-" if speaker else ""
    _write(raw / f"{prefix}context-r{round_index}-{suffix}.json", asdict(pack))
    key = dict(run_id=run_id, round=round_index, speaker=speaker)
    row = dict(key, estimated_tokens=pack.estimated_tokens, actual_tokens=pack.actual_tokens,
               estimation_error=pack.estimation_error, compaction_triggered=pack.compaction_triggered,
               dropped_count=len(pack.dropped), elapsed_ms=pack.elapsed_ms)
    path = results / "context-metrics.json"
    with (raw.parent / ".context-metrics.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = json.loads(path.read_text()) if path.exists() else []
        rows = [r for r in rows if any(r.get(k) != v for k, v in key.items())]
        _write(path, rows + [row])
