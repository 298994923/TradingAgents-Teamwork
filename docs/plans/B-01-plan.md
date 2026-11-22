# Package B implementation and verification plan

Owner: FuKaichao (60468706). S0 approved by the owner in this chat on 2026-11-20 with the message “approve S0”. This plan and the tests await separate reviews. Compare against upstream 9fa1196f and integrate on team main (inspected at 3b23a8de). All behavior below is proposed.

| Invariant | Trigger and statement | Required action on violation |
|---|---|---|
| INV-B1 | Before either first-round invoke, the assembled prompt must exclude opponent claims. | Reject the input and raise before invoking the model. |
| INV-B2 | A targeted response references an assigned, existing, earlier, non-self claim. | Record the reference violation and reject the response. |
| INV-B3 | Each citation resolves through A's checker and satisfies the strict historical cutoff. | Reject the citation and record its specific failure reason. |
| INV-B4 | Every compacted context preserves the count and fingerprint multiset of hard constraints. | Raise ContextBudgetError and suppress the incomplete context. |
| INV-B5 | An invalid structural result allows at most one repair invocation. | Degrade immediately on repeated failure and retain disagreement data and reason. |
| INV-B6 | Every assembly preserves L0 through L5 in order, with hard constraints before evidence. | Reject assembly on a failed order assertion. |

## Stage gates

Commands below are planned verification from the team repository root. S2 test names and subsequent evaluation commands become binding when the test specifications are approved.

| Stage | Input | Output | Verification command | Exit | Failure handling |
|---|---|---|---|---|---|
| S0 | Two pinned baselines | Recon report | python -m pytest -m 'not integration' | Baselines identified and real outputs recorded | Record unavailable facts and causes |
| S1 | Recon and execution brief | Requirements, plan, requests | Parse requirements with yaml.safe_load and validate IDs and fit fields | Testable conditions and human plan approval | Revise before S2 |
| S2 | Approved requirements | Offline tests and 12+ fixtures | python -m pytest test/offline/test_review.py test/offline/test_context_builder.py | Negative and positive cases reviewed, expected initial failures recorded, human test approval | Amend specifications before implementation |
| S3 | Approved review tests | Review protocol and bounded repair | python -m pytest test/offline/test_review.py -k 'claim or evidence or repair' | Validation and degradation cases pass | Fix B implementation |
| S4 | Protocol and C contract | Blind and targeted researcher paths | python -m pytest test/offline/test_review.py -k researcher | Both orders and targeted links pass | Reject leaked or unassigned input |
| S5 | Layer contract and fixtures | Context builder | python -m pytest test/offline/test_context_builder.py | All three budget scenarios pass | Reject invalid packs |
| S6 | Claim ledger and manager cases | Manager output | python -m pytest test/offline/test_review.py -k manager | Adoption and unresolved data survive fallback | Fix manager adapter |
| S7 | Fixed cases and pinned original | Comparison table | python -m pytest test/live/test_baseline_compare.py | Identical inputs documented, every row measured or explained | Mark unavailable rows not_run |
| S8 | D/C/E responses | Versioned schemas and decisions | python -m pytest test/offline | Round-trip and compatibility regressions verified | Resolve affected interface or record pending review |
| S9 | Fixed case set and model | Evaluation report and sanitized tables | python -m pytest test/live/test_review_quality.py | At least three matched repetitions; thresholds assessed | Record misses; unavailable live runs cannot clear gate |
| S10 | Verified schema and prompt text | Contract, ADR and versioned prompts | git diff --check | Verify symbol mappings, recompute prompt hashes and check startup prompt length | Reconcile documentation with tested behavior |
| S11 | Approved versions, evidence and history | Personal submission and PR | git diff --name-only coursework/main...HEAD | Verify scope, reproducibility, approvals, transcript, reflection and demo | Record unresolved items before handoff |

## Risks

| Assumption | Acceptance affected if false | Mitigation |
|---|---|---|
| Scheduler supplies phase and targets | Blind or directed response can be misclassified | Validate phase and targets; keep C's round control |
| Evidence timestamps are available | Historical citation validity cannot be established | Inject timestamp edge cases and reject unknown-time citations in strict mode |
| Hard constraints fit the configured budget | Zero-loss or size limit fails | Reserve constraint space first and explicitly fail impossible budgets |
| Provider and local estimates cover the same input | Token comparison can imply false savings | Aggregate matching node inputs, exclude completion tokens and record missing coverage |
| Team prompt files can be extended safely | Existing versions or teammate changes could be overwritten | Inspect current contents and history; reconcile ownership before S10 |

The requirements file provides candidate trace entries for A. B owns review/context logic, researcher and manager adapters, and agreed schema additions. Shared state, routing, evidence validation, final safety enforcement, metrics writer and CI remain with their respective owners. Keep legacy entry points and original prompts available. Stage reports must distinguish measured results from proposed thresholds.
