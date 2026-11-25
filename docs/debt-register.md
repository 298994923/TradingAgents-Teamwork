# Debt register — open items ledger

Maintained by Role D (Liu Kehong, 60894001). Status: OPEN / REGISTERED / IN PROGRESS / CLOSED.
Last updated: 2026-11-25. No dates are ever backfilled.

| ID | Debt / deviation | Owner | Status | Notes |
|---|---|---|---|---|
| OI-01 | 11 author-self-merges: #21 #32 #37 #48 #51 #52 (C); #34 #35 #41 (B); #42 (E); #49 (D, self-registered) | E | REGISTERED | deviation comments posted with actual dates; amendment proposed 2026-11-25 |
| OI-02 | ai-use-log agent field edited Codex to opencode twice (#41 850a652, #45 05f38b3 via web UI) while git shows Codex authorship | B | OPEN | session-export evidence or restore accurate declarations |
| OI-03 | post-manifest SidecarError double-terminal-write hazard | E | OPEN | capture-enabled stays default-off meanwhile |
| OI-04 | ruff F811 x2 (full-tree lint debt) | C | OPEN | promote offline fixture to conftest; suite stays green |
| OI-05 | B zero gate1 records in docs/approvals/ | B | OPEN | register post-hoc with honest dates |
| OI-06 | PR #3 disposition undecided | D/E | OPEN | 3-day pending |
| OI-07 | D English chapter + reflection not delivered to E | D | IN PROGRESS | draft complete |
| OI-08 | teammate transcripts absent (only 60894001 present) | ALL | OPEN | E sets mode; naming -- vs - to confirm |
| OI-09 | required-tree gaps: root Report.md / Prompt.md / architecture-blueprint.md; trace-matrix / memory-design / option-ledger / evaluation-logbook / risk-list / evaluation-table / runtime-policy-catalog; prompt_v1.1.yaml; adr 001 numbering question | E to assign | OPEN | D three delivered with this register |
| OI-10 | permission-sync drift 10 findings | config owner via E | REGISTERED | fix + exit 0 + one negative probe before submission |
| OI-11 | raw-01 session export outdated | D | OPEN | re-export before final submission |
| OI-12 | who closed original PR #15 unrecorded | — | LOW | historical footnote |
| OI-13 | CI gate-logic updates (gate 4 / gate 6) landed as code | E + reviewer | IN PROGRESS | confirm reviewer + regression; D verifies at next acceptance |

Recorder: Liu Kehong (Role D, 60894001), 2026-11-25.

## Role C — Remaining evaluation and integration work

**Contributor:** LiChengzhi (61023334). These items do not replace the existing governance and operational debt entries.

| ID | Debt / deviation | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| C-OI-01 | Same-revision V0/V1 outcome and usage comparison is not established by the scripted route tests. | C; E records runs | OPEN | Apply the [comparison protocol](architecture/evaluation-table.md); distinguish reported usage from unknown and keep failed attempts in scope. [PR #21](https://github.com/298994923/TradingAgents-Teamwork/pull/21) proves the selector, not decision quality. |
| C-OI-02 | Adaptive execution acceptance remains outside delivered V0/V1. | C, with B/D/E at their interfaces | OPEN | [PR #23](https://github.com/298994923/TradingAgents-Teamwork/pull/23) documents the design. Require an end-to-end eligibility, bounded routing, budget, and safe termination test before claiming delivery. |
| C-OI-03 | Explicit locator recovery with Evidence binding is not delivered by ordinary keyed continuation. | C, with A/E at their interfaces | OPEN | [PR #17](https://github.com/298994923/TradingAgents-Teamwork/pull/17) and [PR #18](https://github.com/298994923/TradingAgents-Teamwork/pull/18) cover storage and keyed lifecycle. [PR #48](https://github.com/298994923/TradingAgents-Teamwork/pull/48) covers fresh capture, not replay or recovery. |
