# ADR-003: visibility, targeted debate and context budgets

Owner: Package B. Implementation verified locally; graph integration and formal cross-package acceptance remain pending (B-07-interface-log). In the upstream debate the second speaker reads the first answer in the common history. Repeating that history also couples a prompt's size to earlier turns. The decision must be independently testable at the model invocation boundary.

| Candidate | Visibility and cost | Decision |
|---|---|---|
| Sequential shared history | Simple append and replay; couples the second opening to the first and repeatedly sends old text. | Retain for legacy comparisons. |
| Fixed rounds with full mutual visibility | A round cap bounds invocations, but either opening can see its peer and each invocation still pays for the full history. | Insufficient for INV-B1. |
| Blind opening, assigned replies, layered compaction | Requires a claim ledger, scheduler targets, validation and additional local processing. Each emitted context has a measurable budget and inspectable dependencies. | Select for collaboration mode. |

## Inputs and assembly

C supplies round and target assignments. The researcher chooses an allowlist of state fields. An opening omits debate history. Later prompts include the speaker's earlier claims and only assigned opponent material. The final opening prompt is checked for normalized opposing text and fingerprints before invocation. The manager validates dispositions against the ledger and returns a delta for C.

| Layer | Contents | Position and retention rationale |
|---|---|---|
| L0 | Role and instrument identity | Establish the subject first; protect the original text. |
| L1 | Hard constraints | Put conditions before evidence; preserve every ID, occurrence and text. |
| L2 | Evidence and existing analysis | Place common observations before the task. Retention favors higher numeric tier, later comparable timestamp strings and higher citation count. |
| L3 | Current task, output format, round and assigned targets | Establish what must be answered; protect the task even under pressure. |
| L4 | Necessary own history | Keep links and attribution on retained blocks; remove routine history first. |
| L5 | Resume state or explicit unknown | Distinguish absent resume data; eligible for trimming after history. |

1. Deduplicate eligible L2/L4 text within each layer and speaker. Output the first occurrence and a duplicate_of record for each duplicate. Fingerprints use NFKC, case folding, punctuation/whitespace normalization and a truncated SHA-256.
2. Determine retention priority from the surviving blocks. L0/L1/L3 are mandatory. Trim L4, then L5, then L2; prefer unresolved, disputed or cited history within L4.
3. Estimate each serialized block, including JSON tags and newline, then sum. The default estimator rounds each block's character length divided by four upward. Researcher default budget is 8192 estimated tokens.
4. Compact when total exceeds budget times compaction_threshold (default 0.85). Equality alone does not trigger. Remove routine history once triggered; trim additional low-priority blocks until the budget fits. Current compaction selects whole blocks; it produces no model-written summary.
5. Reassemble protected L0 and L1 before the remaining layers. Compare ordered ID and full SHA-256 text pairs against the original, preserving multiplicity. Raise ContextBudgetError if the mandatory blocks cannot fit or verification fails.
6. Emit ContextPack plus drop reasons. The researcher sends pack.render() and records any returned provider input usage. Manager decisions use a separate structured contract.

## Token semantics and decision evidence

S9 measured nine researcher prompts against CityU provider input usage. Signed error (estimate minus actual) was -17 for openings, -47 for full targeted prompts and -31 for compacted targets. For the same fixed fixture/model/prompt, the accepted comparison band is the observed interval [-47, -17]; a result outside it triggers investigation. This retrospective reproducibility band does not guarantee a maximum error on new inputs. Output-token counts are separate. JSON formatting, tokenizer boundaries, blockwise rounding and provider chat framing can change the gap. Inclusive graph-node totals may combine rounds; compare only calls with matching coverage.

In three paired trials compaction reduced actual input from 460 to 374 tokens and retained the constraint. S7's offline canary leaked in 2/2 legacy openings and 0/2 collaboration openings. S9 had no repair attempts. Both evaluations use small fixed cases. Review this decision if leakage or hard-constraint loss occurs, provider/model changes invalidate the estimate, the graph cannot carry target IDs, or exact-copy manager reasons exclude useful decisions.

Traceability: B-REQ-01 through B-REQ-12 and INV-B1 through INV-B6 in B-01-plan.md. Reproduce using test/offline/test_review.py, test/offline/test_context_builder.py, test/live/test_baseline_compare.py and test/live/test_review_quality.py. Data: results/B/B-compare-20261120.json and results/B/B-09-eval-2026-11-20.json.
