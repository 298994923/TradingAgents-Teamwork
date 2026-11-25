# C-verification-and-closeout-evidence.md

**Role C discussion draft — prior verification evidence and closeout boundaries, not a formal verdict.**

## Prior offline evidence

| Delivered scope | Observed prior offline result | Public delivery |
|---|---|---|
| Standalone budget policy | 13 policy tests passed; this did not exercise adaptive graph routing. | [PR #4](https://github.com/298994923/TradingAgents-Teamwork/pull/4) |
| Guard opt-in | 129 passes in the expanded candidate selection. | [PR #12](https://github.com/298994923/TradingAgents-Teamwork/pull/12) |
| Keyed checkpoint storage and graph lifecycle | 23 storage tests passed. The later checkpoint selection, including the real receipt path, passed 41 cases. | [PR #17](https://github.com/298994923/TradingAgents-Teamwork/pull/17), [PR #18](https://github.com/298994923/TradingAgents-Teamwork/pull/18), [PR #22](https://github.com/298994923/TradingAgents-Teamwork/pull/22) |
| V1 selector | 14 selector and receipt cases and 41 checkpoint cases passed on the merged candidate. | [PR #21](https://github.com/298994923/TradingAgents-Teamwork/pull/21) |
| Terminal completion | 98 focused and 1,961 full offline tests passed, plus 100 passing subtests. The terminal marker is scoped to normal unguarded V0/V1 final decisions. | [PR #32](https://github.com/298994923/TradingAgents-Teamwork/pull/32), [PR #37](https://github.com/298994923/TradingAgents-Teamwork/pull/37) |
| Fresh Evidence capture | Baseline: one pinned pass and three expected missing-interface failures. Candidate: 4 pinned, 10 supplemental, 99 focused, 14 V1, 41 checkpoint, 21 receipt, and 4 terminal passes. The full run recorded 2,014 passes, 2 skips, 1 deselection, 24 warnings, and 100 passing subtests. | [PR #46](https://github.com/298994923/TradingAgents-Teamwork/pull/46), [PR #47](https://github.com/298994923/TradingAgents-Teamwork/pull/47), [PR #48](https://github.com/298994923/TradingAgents-Teamwork/pull/48) |

These counts are prior recorded offline results, not new runs or GitHub checks. Focused selections overlap and must not be added to full-suite totals. The fresh-capture full run used scripted calls and isolated storage. It skipped the optional `langchain_aws` case and the provider-dependent semantic case.

## Fresh capture traceability

[PR #47](https://github.com/298994923/TradingAgents-Teamwork/pull/47) registered these bindings in `docs/req/evidence-registration-trace.md`. The [delivered CLI test](../../../test/offline/fresh_evidence_capture/test_fresh_evidence_cli_review.py) verifies:

- `REQ-C-CAP-01`: `test_fresh_capture_v0_v1[v0-2]` and `test_fresh_capture_v0_v1[v1-1]` check the barrier, publication order, and manifest reference to the canonical artifact.
- `INV-C-CAP-01`: `test_save_failure_aborts_before_bull` checks the original failure cause, no Bull execution, and a null reference under the reserved run ID.

## Public review and remaining boundaries

- [PR #48](https://github.com/298994923/TradingAgents-Teamwork/pull/48) records a non-author approval on its head and an author-performed merge. [PR #21](https://github.com/298994923/TradingAgents-Teamwork/pull/21) and [PR #37](https://github.com/298994923/TradingAgents-Teamwork/pull/37) also record author-performed merges. Record approval, merge, and check status separately.
- [PR #48](https://github.com/298994923/TradingAgents-Teamwork/pull/48) shows distinct PR and merge-commit checks. The approval and AI-use jobs are PR-only; semantic evaluation is advisory. Passing jobs are not evidence of required branch contexts or protected-path enforcement.
- Terminal completion and failed Evidence save have scoped regression evidence. Capture remains experimental and default-off; the failed-save test does not assert general finalization reliability.
- Explicit locator-based checkpoint resume and adaptive V2 are not included in the delivered-scope claims.

See [C-course-deliverable-inventory.md](C-course-deliverable-inventory.md) for the remaining team assembly.
