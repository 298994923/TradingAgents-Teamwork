# Review and context contract 1.0

## Team main — reviewed behavior

C reviewed 8e6364e. The main source and test references below were checked at 58f8ee5. The graph starts investment_debate_state.count at zero, increments it per Bull/Bear call and routes to Research Manager at twice max_debate_rounds. Explicit V0 runs two pairs and V1 one. Both speakers receive text history and the last response; the first Bear can see Bull. The invocation count does not supply round_index or target_claim_ids. Research Manager uses ResearchPlan or free text, updates investment_debate_state and returns a string investment_plan to Trader.

Bull, Bear and Manager use render_debate_prompt and Python templates. The archived YAML catalogs identify historical prompt versions. input_sha256 fingerprints the actual sent text; role hashes identify templates. A receipt may have a null round and supplies no provider usage. The CLI writes <results_dir>/runs/<run_id>/manifest.json.

The default context cap is 8,192 estimated tokens. Compaction triggers strictly above 0.85 of the cap. In each eligible L2 or L4 layer, the key is exact text plus sorted JSON metadata (all fields except id and text). Equal keys retain the first ID; changes to signs, case, source or priority remain distinguishable. If required context cannot fit, ContextBudgetError precedes the affected call and receipt; the run follows its failure path. Provider-reported input tokens are a separate measurement.

C's standalone execution BudgetPolicy reserves review capacity and can deny an unaffordable optional call before invocation, with zero calls and no settlement. Unknown usage remains unknown. Adaptive budget routing and the V2 example are outside shipped V0/V1. A context exception yields no successful manager delta or budget-stop REVIEW.

Main test selectors:
- test/offline/test_b_context_wiring.py::test_researcher_compacts_history_and_receipts_match_sent_input
- test/offline/test_b_context_wiring.py::test_manager_keeps_latest_arguments_from_both_sides
- test/offline/test_b_context_wiring.py::test_required_context_over_budget_stops_before_call_or_receipt
- test/offline/test_context_builder.py::test_history_priority_survives_deduplication

These cover compacted input and its hash, latest manager arguments, before-send failure, and priority-sensitive deduplication. Blind openings, assigned targets, typed manager deltas and whole-graph budget admission require separate evidence.

On main, ContextPack and LayerBudget are defined in tradingagents.context_builder. tradingagents.agents.schemas provides ResearchPlan and its renderer. Claim, ClaimBatch, ReviewResult and ManagerDecision are coursework types. For a future opt-in integration C must supply separate blind openings (round_index=1, empty targets), then authorized earlier opposing IDs; retain the accepted claim ledger and explicitly track open issues. An absent target or response link cannot close an issue. Validate the outer manager envelope version and shape even when older inner records have defaults. Preserve typed state and render only admissible decisions into the legacy string. Unknown version, invalid or degraded output, renderer rejection and REVIEW must stay off the Trader path. This adapter is proposed.

## Coursework wire contract 1.0, records and defaults

In the B coursework checkout, consumers may import Claim, ClaimBatch, ReviewResult, LayerBudget, ContextPack and ManagerDecision from tradingagents.agents.schemas. Team sources live under src/tradingagents; the upstream checkout uses tradingagents/. Validation happens at the producer before a state delta is accepted.

| Record / fields | Type | Required or default | Constraint and consumer meaning |
|---|---|---|---|
| Claim.claim_id, speaker | string, bull or bear | Required | Unique ID across prior ledger and current batch; speaker must match the invoked role. |
| Claim.statement, fingerprint | string, 16 lowercase hex | Statement required; fingerprint derived | Nonblank text, default cap 2000 characters. The digest identifies normalized text. |
| Claim.round_index, responds_to | positive integer, string list | Required | Opening has no links. Later claims must cite an assigned earlier opposing claim. |
| Claim.evidence_ids, unresolved_questions | string lists | Required | At least one valid citation; questions may be empty. Historical checks depend on A's injected oracle returning (ok, reason). |
| ClaimBatch.claims, schema_version | Claim list, literal 1.0 | Claims required; version defaults to 1.0 | validate rejects empty batches and clears partial successes on violation. |
| ReviewResult.status, claims, violations | enum, Claim list, Violation list | ok, empty lists | Status is ok, violation or degraded. Violation carries code, field and detail strings. |
| ReviewResult.repaired, repair_attempts, degraded | bool, integer, bool | false, 0, false | At most one structural repair call. |
| ReviewResult.reason, raw_hash, unresolved_questions, schema_version | nullable strings, string list, version | null, null, empty, 1.0 | Retain recoverable questions, the original payload digest and an explicit degradation reason. Earlier ledger entries remain available. Unreadable payloads cannot supply new questions. |
| Block.layer, id, text, metadata | strings, mapping | First three required; metadata defaults empty | Ordered L0 through L5 blocks. Text and metadata enter the estimate. |
| Dropped.id, reason, duplicate_of | strings, nullable ID | ID/reason required; duplicate_of defaults null | Describes omission, including the first retained matching ID for duplicates. |
| ContextPack.blocks, budget, per_layer_tokens | Block list, positive integer, LayerBudget | Required | LayerBudget maps layer names to nonnegative integer estimates. Producer emits all six keys. |
| total_tokens, estimated_tokens | integers | Required | Sum of estimates for emitted blocks; total_tokens is the same estimate. |
| actual_tokens, estimation_error | nullable integers | Required, null allowed | Provider input count and estimated minus actual. Missing usage adds an explicit warning. |
| compaction_triggered, reinjected_constraint_ids | bool, ID list | Required | Records crossing the threshold and L1 IDs checked at reassembly. |
| dropped, warnings, elapsed_ms | Dropped list, string list, number | Required | Reasons and local build time in milliseconds. |
| version, schema_version | literal 1.0 | Default 1.0 | ContextPack retains the original version field alongside the wire schema version. |
| ManagerDecision.adopted_claims, rejected_claims | ClaimDisposition lists | Required | Each claim_id occurs once across both; reason copies its statement or an open question. |
| unresolved_disagreements | OpenDisagreement list | Required | Preserve bull_claim_id, bear_claim_id, why_unresolved and decision_impact exactly. IDs must resolve to the specified speakers. |
| decision_summary, evidence_refs | enum, string list | Required | BUY, OVERWEIGHT, HOLD, UNDERWEIGHT, SELL or REVIEW. Adopted evidence must be covered; every cited ID must resolve through the checker and ledger. |

## Coursework violations and downstream actions

| Code or exception | Trigger | Severity | Action |
|---|---|---|---|
| MISSING_FIELD, EMPTY_STATEMENT, TOO_LONG | Absent/invalid required field, blank statement or cap exceeded | Invalid batch | Reject; parse_with_repair may attempt a safe structural fix for missing fields or excess length. |
| DUP_ID, BAD_RESPONDS_TO, FUTURE_REF | ID collision, invalid assignment/self reference, or target outside an earlier round | Invalid reference | Reject batch. Duplicate IDs in manager ledger raise before invocation. |
| INVALID_EVIDENCE | Empty, malformed, missing or unusable citation | Invalid reference | Reject citation/batch; preserve checker detail. |
| BLIND_CONTEXT_LEAK | Normalized opponent statement or its fingerprint appears in the assembled opening | Blocking | Raise before model invocation. |
| NO_TARGET, INVALID_TARGET | No assignment or unknown/ineligible assignment | Turn violation | Researcher returns a reason and keeps the ledger; invalid manager input linkage raises. |
| ContextBudgetError | Required layers exceed budget or protected text changes | Blocking | Suppress incomplete context. |
| REPAIR_UNAVAILABLE, REPAIR_REJECTED, REPAIR_FAILED | No repair callable, changed/invalid candidate, or failed repair | Degraded | Stop, retain original digest and recoverable disagreements; archive original text locally. |
| INVALID_DISAGREEMENT | Invalid open pair or missing impact/reason | Invalid ledger | Stop before manager invocation. |
| INVALID_MANAGER_FIELDS, INVALID_MANAGER_LIST, INVALID_DISPOSITION, INVALID_MANAGER_OUTPUT | Manager object, array, disposition or value has invalid shape | Invalid response | Validate one repair when supplied; otherwise degrade. |
| INVALID_CLAIM_REFERENCE, UNGROUNDED_REASON, DISAGREEMENT_CHANGED | Untraceable disposition, invented explanation or altered open pair | Invalid response | Reject; preserve input disagreement records on fallback. |
| INVALID_SUMMARY, REVIEW_REQUIRED | Illegal summary or unsupported directional decision | Invalid decision | Reject; use REVIEW on degradation. |

The manager emits content plus state_delta. On degradation, the delta carries investment_plan, unresolved_questions, reason, repair_attempts, degraded and schema_version. Its plan preserves open pairs, clears untrusted dispositions and evidence references, and sets decision_summary to REVIEW. C owns graph writes and legacy text conversion.

## Coursework compatibility, metrics and placement

New optional fields with defaults are backward compatible. Semantic changes require a version bump and explicit migration. Old typed context payloads lacking schema_version default to 1.0; an unknown version fails typed deserialization. Do not silently resume across incompatible meanings. Tests: test_schema_wire_round_trip and test_manager_decision.

Raw prompt snapshots and failed repair payloads belong under outputs/B/<run_id>/. Sanitized context measurements go to results/B/context-metrics.json; comparison and evaluation summaries belong in results/B/. The historical coursework manifest at results/<ticker>/<trade_date>/metrics.json is read-only for B. Provider run/node totals require matched coverage before reconciliation. Text fingerprints support lexical deduplication only. Semantic deduplication, billing guarantees and cross-run semantic merging are outside the contract.

## Coursework artifact provenance script

Run from the checkout root with PyYAML. This verifies all three runtime catalogs and the exact pre-metadata file bytes used for S9.

```python
import hashlib, json
from pathlib import Path
import yaml

raw = Path("prompts/prompt_v1.0.yaml").read_bytes()
doc = yaml.safe_load(raw)
for item in doc["prompt_catalog"]:
    texts = {k: doc["researchers"][k] for k in item["text_keys"]}
    canonical = json.dumps(texts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode()).hexdigest() == item["prompt_sha256"]
s9 = json.loads(Path("results/B/B-09-eval-2026-11-20.json").read_text())
assert hashlib.sha256(raw.split(b"# S10 provenance metadata\n")[0]).hexdigest() == s9["prompt_sha256"]
```


On 2026-11-20 the fixed coursework S9 run reported 6/6 targeted replies. On 2026-11-24 the offline replay used simulated responses: v1.0 and v1.1 each recorded target hits 0/6 and structural validity 0/12. Each version verified 12/12 input receipts. Both functional criteria failed in that replay. Relative live-model quality remains unmeasured.
