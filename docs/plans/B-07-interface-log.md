# S8 interface decisions

FuKaichao, 60468706. S7 approved by the owner in chat. Evidence boundary: team main 3b23a8de (GitHub recursive tree checked again at S8), S1 request draft and the implemented producer fields. No incoming C/D/E field request or sign-off was identified in that snapshot. The decisions below are B's dispositions on the proposals. An absent reply remains pending.

| Party | Field or request | B verdict and reason | Affected symbols | Verification or open dependency |
|---|---|---|---|---|
| C | Claim ledger, round_index, assigned targets and unresolved questions | Accept for B node inputs. Defer shared state and checkpoint wiring to C; the legacy graph still expects investment_plan as text. | ClaimBatch, ReviewResult, manager state_delta | Team graph regression passed with legacy defaults. C must confirm mapping of the structured delta and unknown-version handling before enabling collab in the graph. |
| D | Adopted/rejected IDs and reasons, open bull/bear IDs, why unresolved, decision impact and REVIEW | Accept as B output. Defer extra hard-constraint fields until D supplies their semantics and negative cases. | ManagerDecision, ClaimDisposition, OpenDisagreement | Round trip and manager tests pass. D's downstream acceptance is pending. |
| E | Versioned context, per-layer estimates, elapsed time, dropped IDs, optional provider input usage | Accept in B sidecar. Defer shared event extensions until E supplies its event envelope. | ContextPack, LayerBudget, write_context_artifacts | Round trip and placement tests pass. Event integration and publishing ignored results are pending. |
| E / NanLi | Extend shared metrics.json | Defer. The existing node buckets lack round granularity; B can publish its estimate without changing existing readers. | Team reporting.write_run_manifest; B context-metrics.json | NanLi authored the implementation (47545b6ca2); formal schema approver remains unconfirmed. |

## Version and field rules

- Claim requires claim_id, bull/bear speaker, statement, evidence_ids, responds_to, unresolved_questions, positive round_index and a 16-character hexadecimal fingerprint. The pure validator checks reference integrity and evidence before a claim enters the ledger.
- ClaimBatch requires the claims list. It, ReviewResult and ContextPack use schema_version 1.0. Omission on old wire data defaults to 1.0. A different literal fails typed deserialization. Backward-compatible additions require defaults; semantic changes require a version bump and explicit migration.
- ReviewResult defaults to ok with empty collections, zero repair calls, no reason or hash and false flags. Its wire repair count is restricted to zero or one. Business checks remain in review.validate.
- LayerBudget describes the existing per_layer_tokens mapping, indexed by L0 through L5 with nonnegative integers. build emits all six keys. ContextPack retains its prior version field, ordered blocks, budget, totals, nullable actual usage/error, drop records and warnings. Missing usage is explicitly marked unavailable.
- ManagerDecision requires all five S6 fields. The version is on state_delta, outside the decision payload. Typed deserialization checks field shapes; the manager checks references, evidence and disagreement preservation against the live ledger.
- B-side metrics are keyed by run, round and speaker. The run ID must be aligned with E's recorded run before comparing to a manifest. NanLi's authorship is historical evidence, not approval authority.

## Verification

Local offline tests plus the matched comparison: 30 passed. In an isolated copy of the pinned team tree, compared each existing target against upstream before applying B changes, retained the team's YAML keys and ran the full test/offline directory with PYTHONPATH=src. Result: 1452 passed, 1 skipped, 1 deselected, 24 warnings, 100 subtests passed in 14.05s. The optional Bedrock SDK test skipped; integration was deselected. This includes the existing test_graph_end_to_end.py. No new C collaboration routing suite was found. External verdicts, shared checkpoint/event integration and the formal metrics approver remain open.
