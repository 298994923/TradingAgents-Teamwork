"""Package B investment debate claim validation and bounded format repair."""

import hashlib
import json
from tradingagents.run_recorder import RUN_ID_PATTERN
import unicodedata
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

MAX_REPAIR_ATTEMPTS = 1
DEFAULT_STATEMENT_CAP = 2000


def fingerprint(text):
    """Compute a fingerprint for text-level dedup only; does not detect semantic duplicates."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    spaced = "".join(" " if unicodedata.category(c).startswith("P") else c for c in folded)
    normalized = " ".join(spaced.split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


@dataclass
class Claim:
    claim_id: str
    speaker: Literal["bull", "bear"]
    statement: str
    evidence_ids: list[str]
    responds_to: list[str]
    unresolved_questions: list[str]
    round_index: Annotated[int, Field(ge=1)]
    fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]


@dataclass
class ClaimBatch:
    claims: list[Claim]
    schema_version: Literal["1.0"] = "1.0"


@dataclass
class Violation:
    code: str
    field: str
    detail: str


@dataclass
class ReviewResult:
    status: Literal["ok", "violation", "degraded"] = "ok"
    claims: list[Claim] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    repaired: bool = False
    repair_attempts: Annotated[int, Field(ge=0, le=1)] = 0
    degraded: bool = False
    reason: str | None = None
    raw_hash: str | None = None
    schema_version: Literal["1.0"] = "1.0"

    def reject(self, code, name, detail):
        self.status = "violation"
        self.violations.append(Violation(code, name, detail))


def _mapping(item):
    if isinstance(item, Claim):
        return asdict(item)
    return item if isinstance(item, Mapping) else {}


def _string_list(value):
    return isinstance(value, list) and all(isinstance(s, str) and s.strip() for s in value)


def validate(claims, *, prior_claims, evidence_checker, statement_cap=DEFAULT_STATEMENT_CAP):
    """Validate one atomic batch against an earlier ledger and an injected evidence oracle."""
    result = ReviewResult()
    ledger = {}
    for item in prior_claims:
        prior = _mapping(item)
        if isinstance(prior.get("claim_id"), str):
            ledger[prior["claim_id"]] = prior
    seen = set(ledger)
    if isinstance(claims, ClaimBatch):
        claims = claims.claims
    if not isinstance(claims, list) or not claims:
        result.reject("MISSING_FIELD", "claims", "Expected a nonempty list")
        return result

    for item in claims:
        claim = _mapping(item)
        before = len(result.violations)
        for name in ("claim_id", "speaker", "statement", "round_index", "responds_to",
                     "unresolved_questions", "evidence_ids"):
            if name not in claim:
                result.reject("MISSING_FIELD", name, "Required field absent")
        identifier = claim.get("claim_id")
        if not isinstance(identifier, str) or not identifier.strip():
            result.reject("MISSING_FIELD", "claim_id", "Expected a nonempty identifier")
        elif identifier in seen:
            result.reject("DUP_ID", "claim_id", identifier)
        else:
            seen.add(identifier)
        speaker = claim.get("speaker")
        if speaker not in ("bull", "bear"):
            result.reject("MISSING_FIELD", "speaker", "Expected bull or bear")
        statement = claim.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            result.reject("EMPTY_STATEMENT", "statement", "Expected nonempty text")
        elif len(statement) > statement_cap:
            result.reject("TOO_LONG", "statement", f"Maximum length is {statement_cap}")

        questions = claim.get("unresolved_questions")
        if _string_list(questions):
            result.unresolved_questions.extend(questions)
        else:
            result.reject("MISSING_FIELD", "unresolved_questions", "Expected a list of questions")
        round_index = claim.get("round_index")
        targets = claim.get("responds_to")
        if type(round_index) is not int or round_index < 1:
            result.reject("MISSING_FIELD", "round_index", "Expected a positive integer")
        elif not _string_list(targets) or bool(targets) != (round_index > 1):
            result.reject("BAD_RESPONDS_TO", "responds_to", "Invalid targets for this round")
        else:
            for target in targets:
                prior = ledger.get(target)
                if not prior or target == identifier or prior.get("speaker") == speaker:
                    result.reject("BAD_RESPONDS_TO", "responds_to", target)
                elif type(prior.get("round_index")) is not int or prior["round_index"] >= round_index:
                    result.reject("FUTURE_REF", "responds_to", target)

        evidence = claim.get("evidence_ids")
        if not evidence:
            result.reject("INVALID_EVIDENCE", "evidence_ids", "EMPTY")
        elif not _string_list(evidence):
            result.reject("INVALID_EVIDENCE", "evidence_ids", "MALFORMED")
        else:
            for key in evidence:
                ok, reason = evidence_checker(key)
                if ok is not True:
                    result.reject("INVALID_EVIDENCE", "evidence_ids", f"{reason}: {key}")

        if len(result.violations) == before:
            result.claims.append(Claim(identifier, speaker, statement, list(evidence),
                                       list(targets), list(questions), round_index, fingerprint(statement)))
    if result.violations:
        result.claims.clear()
    return result


def _decode(raw):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("Duplicate JSON key")
            obj[key] = value
        return obj
    return json.loads(raw, object_pairs_hook=unique)


def _recover(raw):
    """Recover only missing terminal delimiters without guessing claim content."""
    stack = []
    quoted = escaped = False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == chr(92):
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            stack.append("]" if char == "[" else "}")
        elif char in "]}":
            if not stack or stack.pop() != char:
                raise ValueError("Mismatched delimiter")
    return _decode(raw + "".join(reversed(stack)))


def parse_with_repair(raw, *, repair, prior_claims, evidence_checker, output_root, run_id,
                      statement_cap=DEFAULT_STATEMENT_CAP):
    """Accept a repair only when its parsed content matches the safe reconstruction."""
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("Invalid run identifier")
    digest = hashlib.sha256(raw.encode()).hexdigest()

    def check(batch):
        return validate(_mapping(batch).get("claims"), prior_claims=prior_claims,
                        evidence_checker=evidence_checker, statement_cap=statement_cap)

    try:
        original = _decode(raw)
    except ValueError:
        original = None
    else:
        result = check(original)
        result.raw_hash = digest
        if result.status == "ok" or any(v.code not in ("MISSING_FIELD", "TOO_LONG")
                                        for v in result.violations):
            return result

    result = ReviewResult(raw_hash=digest)
    try:
        safe = _recover(raw)
        for claim in _mapping(safe).get("claims", []):
            if not isinstance(claim, dict):
                continue
            claim.setdefault("unresolved_questions", [])
            if claim.get("round_index") == 1:
                claim.setdefault("responds_to", [])
            if isinstance(claim.get("statement"), str):
                claim["statement"] = claim["statement"][:statement_cap]
        result = check(safe)
    except (ValueError, TypeError):
        safe = None
    result.raw_hash = digest
    reason = "REPAIR_UNAVAILABLE"
    if repair is not None:
        result.repair_attempts = MAX_REPAIR_ATTEMPTS
        try:
            candidate = _decode(repair(raw))
            if safe is not None and json.dumps(candidate, sort_keys=True) == json.dumps(safe, sort_keys=True) and result.status == "ok":
                result.repaired = True
                return result
            reason = "REPAIR_REJECTED"
        except Exception:
            reason = "REPAIR_FAILED"
    result.status = "degraded"
    result.degraded = True
    result.reason = reason
    result.claims.clear()
    directory = Path(output_root) / "B" / run_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"repair-raw-{digest}.txt").write_text(raw, encoding="utf-8")
    return result


def _prompt_document():
    import yaml

    path = next((parent / "prompts/prompt_v1.0.yaml" for parent in Path(__file__).resolve().parents
                 if (parent / "prompts/prompt_v1.0.yaml").is_file()), None)
    if path is None:
        raise FileNotFoundError("Missing researcher prompt v1.0")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def researcher_prompt(key):
    return _prompt_document()["researchers"][key]


def prompt_hashes(role):
    document = _prompt_document()
    entry = next(item for item in document["prompt_catalog"] if item["role"] == role)
    texts = {key: document["researchers"][key] for key in entry["text_keys"]}
    payload = json.dumps(texts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()
    if digest != entry["prompt_sha256"]:
        raise ValueError("PROMPT_HASH_MISMATCH")
    return {entry["id"]: digest}


def legacy_prompt_observer(on_prompt, role, template, state):
    """Hash the exact static template used to render this legacy role."""
    if on_prompt is None:
        return None
    digest = hashlib.sha256(template.encode("utf-8")).hexdigest()

    def observe(prompt):
        on_prompt(dict(role=role, run_id=state.get("run_id"),
                       round_index=state["investment_debate_state"].get("round_index"),
                       prompt_hashes={"b." + role: digest},
                       input_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest()))
    return observe


def invoke_review_prompt(llm, prompt, role, state, on_prompt):
    if on_prompt is not None:
        on_prompt({
            "run_id": state.get("run_id"),
            "round_index": state["investment_debate_state"].get("round_index"),
            "role": role,
            "prompt_hashes": prompt_hashes(role),
            "input_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        })
    return llm.invoke(prompt)


def _visible_text(text):
    return " ".join("".join(" " if unicodedata.category(c).startswith("P") else c
                            for c in unicodedata.normalize("NFKC", text).casefold()).split())


def create_collab_researcher(llm, speaker, *, evidence_checker, output_root="outputs", repair=None, on_prompt=None):
    from tradingagents.agents.context import get_instrument_context_from_state

    def node(state):
        debate = state["investment_debate_state"]
        number = debate["round_index"]
        if type(number) is not int or number < 1:
            raise ValueError("Invalid round_index")
        run_id = state["run_id"]
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("Invalid run identifier")
        ledger = debate.get("claims", [])
        blind = number == 1
        targets = [] if blind else debate.get("target_claim_ids", [])
        context = dict(round_index=number, blind=blind, speaker=speaker,
                       instrument=get_instrument_context_from_state(state),
                       hard_constraints=state["hard_constraints"], evidence=state["shared_evidence"],
                       analysis={k: state.get(k, "") for k in ("market_report", "sentiment_report",
                                 "news_report", "fundamentals_report")})
        questions = [] if blind else debate.get("target_questions", [])
        # An assigned unresolved question must resolve to an earlier opponent claim.
        eligible = [c for c in ledger if c["speaker"] != speaker and c["round_index"] < number]
        unknown_question = any(not any(q in c.get("unresolved_questions", []) for c in eligible)
                               for q in questions)
        if questions:
            targets = list(dict.fromkeys([*targets, *(c["claim_id"] for c in eligible
                           if any(q in c.get("unresolved_questions", []) for q in questions))]))
            context["target_questions"] = questions
        selected = [c for c in ledger if c["claim_id"] in targets and
                    c["speaker"] != speaker and c["round_index"] < number]
        if not blind:
            context.update(prior_claims=[c for c in ledger if c["speaker"] == speaker
                                         and c["round_index"] < number], targets=selected)
        phase = "blind" if blind else "respond"
        from tradingagents.context_builder import DEFAULT_THRESHOLD, assert_blind, build, write_context_artifacts

        def block(key, value):
            text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            return {"id": str(key), "text": text}

        def entries(values, prefix):
            if not isinstance(values, list):
                values = [values]
            result = []
            for i, value in enumerate(values):
                key = value.get("id", f"{prefix}-{i}") if isinstance(value, dict) else f"{prefix}-{i}"
                entry = block(key, value)
                if isinstance(value, dict):
                    if isinstance(value.get("text"), str):
                        entry["text"] = value["text"]
                    entry.update({k: v for k, v in value.items() if k not in ("id", "text")})
                result.append(entry)
            return result

        layers = {
            "L0": [block("speaker", speaker), block("role", researcher_prompt(speaker)),
                   block("instrument", context["instrument"])],
            "L1": entries(context["hard_constraints"], "constraint"),
            "L2": entries(context["evidence"], "evidence") +
                  [block(k, v) for k, v in context["analysis"].items() if v],
            "L3": [block("task", researcher_prompt(phase)), block("format", researcher_prompt("format")),
                   block("phase", {"round_index": number, "blind": blind})],
            "L4": [],
            "L5": [],
        }
        if not blind:
            layers["L3"].extend(block(c["claim_id"], c) for c in selected)
            if questions:
                layers["L3"].append(block("target_questions", questions))
            layers["L4"] = [dict(block(c["claim_id"], c), speaker=speaker,
                                 unresolved=bool(c.get("unresolved_questions")))
                            for c in context["prior_claims"]]
        pack = build(layers, state.get("context_budget", 8192),
                     compaction_threshold=state.get("compaction_threshold", DEFAULT_THRESHOLD))
        prompt = pack.render()
        if blind:
            assert_blind(prompt, opponent_claims=[c for c in ledger if c["speaker"] != speaker])
        directory = Path(output_root) / "B" / run_id
        directory.mkdir(parents=True, exist_ok=True)
        # Each speaker keeps its own snapshot even when their turns share a round.
        name = f"context-r{number}-{phase}.json"
        snapshot = json.dumps(context, ensure_ascii=False, indent=2)
        (directory / f"{speaker}-{name}").write_text(snapshot, encoding="utf-8")
        (directory / name).write_text(snapshot, encoding="utf-8")
        updated = dict(debate, count=debate.get("count", 0) + 1)
        if not blind and (unknown_question or not targets or set(targets) != {c["claim_id"] for c in selected}):
            updated.pop("review_result", None)
            updated["review_reason"] = "INVALID_TARGET" if targets or unknown_question else "NO_TARGET"
            updated["review_status"] = "violation"
            return {"investment_debate_state": updated}

        response = invoke_review_prompt(llm, prompt, speaker, state, on_prompt)
        usage = getattr(response, "usage_metadata", None)
        if usage:
            pack = build(layers, pack.budget, actual_usage=usage,
                         compaction_threshold=state.get("compaction_threshold", DEFAULT_THRESHOLD))
        output_path = Path(output_root)
        artifact_root = output_path.parent if output_path.name == "outputs" else output_path
        write_context_artifacts(pack, root=artifact_root, run_id=run_id, round_index=number, speaker=speaker)
        result = parse_with_repair(response.content, repair=repair, prior_claims=ledger,
                                   evidence_checker=evidence_checker, output_root=output_root, run_id=run_id)
        for claim in result.claims:
            if claim.speaker != speaker or claim.round_index != number or not set(claim.responds_to) <= set(targets):
                result.reject("BAD_RESPONDS_TO", "responds_to", "Unexpected speaker, round or target")
                result.claims.clear()
                break
        updated.update(claims=[*ledger, *(asdict(c) for c in result.claims)],
                       review_status=result.status, review_reason=result.reason,
                       review_result=asdict(result),
                       unresolved_questions=list(dict.fromkeys([*debate.get("unresolved_questions", []),
                                                                *result.unresolved_questions])))
        return {"investment_debate_state": updated}

    return node


def validate_manager_refs(adopted, rejected, refs, ledger, evidence_checker):
    """Check disposition IDs, attributed reasons and evidence against the debate ledger."""
    seen = set()
    for item in [*adopted, *rejected]:
        key = item["claim_id"]
        if key not in ledger or key in seen:
            raise ValueError("INVALID_CLAIM_REFERENCE")
        seen.add(key)
        claim = ledger[key]
        if item["reason"] not in [claim["statement"], *claim.get("unresolved_questions", [])]:
            raise ValueError("UNGROUNDED_REASON")
    allowed = {ref for claim in ledger.values() for ref in claim["evidence_ids"]}
    required = {ref for item in adopted for ref in ledger[item["claim_id"]]["evidence_ids"]}
    if not required <= set(refs) <= allowed or any(evidence_checker(ref)[0] is not True for ref in refs):
        raise ValueError("INVALID_EVIDENCE")


def snapshot_evidence_checker(api, snapshot, references, *, historical=True):
    """Bind B's citation keys to the original qualified references supplied by C."""
    def check(key):
        ref = references.get(key)
        if ref is None:
            return False, "MISSING"
        result = api.validate_reference(snapshot, ref)
        if (result.structure, result.binding, result.slot, result.availability) != (
                "conformant", "matched", "found", "present"):
            return False, ",".join(result.reasons) or "INVALID_EVIDENCE"
        # Evidence V1 has no source-availability timestamps. Newer evidence
        # contracts need explicit cutoff validation before historical use.
        return (False, "UNKNOWN_TIME") if historical else (True, "OK")

    return check
