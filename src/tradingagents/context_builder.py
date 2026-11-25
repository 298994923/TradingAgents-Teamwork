"""Ordered debate context. Character-based estimates are not provider billing."""
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Annotated, Literal

from pydantic import Field

LAYERS = ("L0", "L1", "L2", "L3", "L4", "L5")
DEFAULT_THRESHOLD = 0.85
DEFAULT_BUDGET = 8192
_TURN_START = re.compile(r"(?m)^(Bull|Bear) Analyst:")


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
            if layer in ("L2", "L4"):
                # Preserve signs, source metadata, and priority distinctions.
                # For exact copies, retain the first ID and record the alias.
                key = text, json.dumps(meta, sort_keys=True, ensure_ascii=False)
                if key in seen:
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


def render_debate_prompt(template, values, language, *, evidence_fields=(), budget=DEFAULT_BUDGET):
    """Fit debate inputs to a local estimate while keeping the existing prompt format."""
    full_prompt = template.format_map(values) + language
    if _estimate(full_prompt) <= budget * DEFAULT_THRESHOLD:
        return full_prompt

    history = values["history"]
    starts = list(_TURN_START.finditer(history))
    ends = [match.start() for match in starts[1:]] + [len(history)] if starts else []
    turns = [
        (match.group(1), history[match.start():end].rstrip("\n"))
        for match, end in zip(starts, ends, strict=True)
    ]
    prefix = history[:starts[0].start()] if starts else history
    turns = [(None, line) for line in prefix.splitlines() if line.strip()] + turns

    # The latest argument from either side stays available to the manager.
    recent = {speaker: index for index, (speaker, _) in enumerate(turns) if speaker}
    protected_indices = set(recent.values()) if "current_response" not in values else set()
    excerpt = [{"id": str(index), "text": text, "speaker": speaker}
               for index, (speaker, text) in enumerate(turns)]

    reduced = {**values, "history": "", **dict.fromkeys(evidence_fields, "")}
    fixed = template.format_map(reduced) + language
    parts = {
        "L1": [{"id": "fixed-prompt", "text": fixed}],
        "L2": [{"id": name, "text": values[name], "tier": index}
               for index, name in enumerate(evidence_fields)],
        "L3": [entry for index, entry in enumerate(excerpt) if index in protected_indices],
        "L4": [entry for index, entry in enumerate(excerpt) if index not in protected_indices],
    }
    pack = build(parts, budget)
    kept_history = []
    for block in pack.blocks:
        if block.layer == "L2":
            reduced[block.id] = block.text
        elif block.layer in {"L3", "L4"}:
            kept_history.append((int(block.id), block.text))
    reduced["history"] = "\n".join(text for _, text in sorted(kept_history))
    return template.format_map(reduced) + language
