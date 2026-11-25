# OpenCode Session Transcripts & Human-Supervision Annotations — Liu Kehong (Student ID: 60894001, Role D)

- Repository / branch: TradingAgents-Teamwork · d-safety-guard
- Agent: OpenCode 1.18.35, model deepseek-v4.1-flash
- Raw records: `transcripts/raw-01..06-*.json` (exported via `opencode export <session-id>`, unmodified)
- Nature of this file: **human annotations**. It records my (the human's) decisions in each
  session: approvals, rejections, corrections, acceptance.
- Boundary statement: all proposals came from the AI; no code before I approved the plan, no
  test passed without an independent member's re-confirmation, and every commit, push and
  merge was executed by me. Formal approval records: `docs/approvals/` and `docs/approvals.yaml`.

> Annotation tags: **Decision** = my call; **Rejected/corrected** = where I pushed the AI back
> or fixed its course.

---

## Session 1 · D safety requirements & invariants plan (raw-04-requirements.json, 11/21 ~19:24)

Task: translate the course requirements into testable Role-D requirements (13 REQ-D items)
and 8 invariants (INV-D series); draft ADR-005.

Annotations:
- **Decision** I set "unknown ≠ known" as the global rule: any unknown source or input is
  fail-closed and must never be treated as known downstream; the severity lattice only
  escalates (BLOCK > REVIEW > PASS). The tolerance is pinned at 1e-9 relative error so the
  fixtures and the implementation measure with the same ruler — no "loose tests, tight code".
- **Rejected/corrected** fixture d7-lattice had a self-contradicting expectation (a PASS
  expected on top of an existing terminal REVIEW). I rejected it and re-ruled: per "REVIEW is
  terminal and irreversible" the expectation became REVIEW_TERMINAL — and I did not decide
  alone: Zhang Ruiqi gave an independent re-confirmation before it landed (gate-1 archive,
  Addendum 1).
- I originally wanted a separate "ultra-large trades require review" requirement; it
  overlapped with the 10% NAV position cap, so it was dropped after review.

## Session 2 · Governance docs plan: structural / verification / MCP manifest (raw-05-codegovernance.json, 11/21 ~15:00)

Task: draft the three docs/code-governance/ files (structural constraints, verification
constraints, MCP tool manifest).

Annotations:
- **Decision** "All MCP tools disabled by default" is not laziness — the course requires
  declaring what is used and never touching what is not. We use no MCP tools at all, so the
  safest declaration is a full deny; anyone who wants one later must change the declaration
  through approval.
- **Decision** The verification checklist is fixed at six gates (test-approval / static /
  schema / semantic evaluation / regression / AI-use-log), matching the machine-checkable
  items in course §12 — we build what the grader checks, nothing decorative.

## Session 3 · Governance docs refactored to role-agnostic permissions (raw-06-roleagnostic.json, 11/21 ~14:50)

Task: change permission clauses from naming persons to naming roles.

Annotations:
- **Decision** Two hard reasons for role-agnostic rules: final grading traces evidence by
  role, so clauses must reference roles; and rules that carry a person's name read as
  "someone's personal policy" — team pushback, and they break on rotation. Roles are the
  subject of rules; names are the trace of actions (approvals, commits). Two systems,
  each doing its own job.

## Session 4 · AGENTS.md governance file (raw-03-agentsmd.json, 11/21 ~22:55)

Task: draft the team AGENTS.md; revise per C's CHANGES REQUIRED review.

Annotations:
- **Rejected/corrected** I implemented every point of C's review (three-tier permission
  table, default deny, baseline-hash correction, stop rules, transcripts marked
  human-only) with no discounting — because every point tightened safety; criticism that is
  directionally right gives me no reason to push back.
- **Decision** I insisted on writing in stone that "an agent must never commit / push /
  open a PR / merge without human authorization": outbound git operations are irreversible,
  and autonomous agent commits are the textbook incident the course red lines target.

## Session 5 · D governance-documents drafting plan (raw-02-govdocs.json, 11/21 ~23:29)

Task: late-night governance round — permission model and cross-document consistency.

Annotations:
- **Decision** This round ran past midnight; B's gate-1 re-review signature is timestamped
  23:54. What keeps continuity across days is not memory but the approvals archive and the
  red-run logs — every decision on paper is how you know "where I left off".

## Session 6 · Test-first deterministic guard (raw-01-testfirst.json, started 11/21 late night · ran all day 11/22)

Task and supervision chain (each step executed/approved by me, all on record):
1. Test first: 63 fixtures + 2 test files, five red runs (red-run-01..05.txt), zero
   implementation code during that phase;
2. Gate 1: B's re-review APPROVE (2026-11-21 23:54, target commit 2205109…) before any
   implementation was allowed;
3. Implementation: 88/88 green (green-run-01.txt), zero upstream regressions;
4. Wiring: six red wiring tests re-confirmed (Addendum 2), then the dual-gate opt-in wiring,
   94 green;
5. 11/22: merge-conflict adjudication (D's governance-file versions retained), AI-use-log
   backfill, guard_result contract key, lint fixes, backfilled approval records (confirmed
   by Role C, with the original approvers noted in comments) → all five checks green on PR #6.

Annotations:
- **Decision — the core question**: why can't a BLOCK be downgraded by a later, more
  persuasive conclusion? Because BLOCK is the gate's deterministic finding of fact — over
  the cap is over the cap, forbidden ticker is forbidden ticker. If some later, more
  articulate model could pull its severity back, the gate would be decoration; the gate
  exists precisely because it sits after everything that talks best. So the merge only
  escalates, REVIEW is terminal too, and any reversal means re-running with the missing
  facts supplied — never through rhetoric.
- **Rejected/corrected** across all five red runs I only fixed the tests' own mistakes and
  never loosened an assertion; when inputs were missing, the AI leaned toward "supply a
  default and continue" — I locked the rule instead: pass the ABSENT sentinel and let the
  gate adjudicate REVIEW. Missing means admitting it is missing; fabrication is not allowed.
- **Decision** the wiring ships opt-in (`state["guard_enabled"]`): force-enabling everything
  at once would break 1412 upstream baseline tests and teammates' unprepared paths; opt-in
  buys zero regression, at the cost of "someone might forget to enable it" — and that cost
  is sealed by another rule: budget enabled with guard disabled is refused at startup as
  CONFIG_INVALID. There is no way to slip through.
- I first considered adopting E's version during the conflict, but worried that later
  document edits would clash again and need rework, so in the end I kept my own version.

---

## Commit record

- This file is committed in the same commit as raw-*.json (2026-11-22).
- Pre-commit security check: secret scan via grep passed (see commit message).

Signed: Liu Kehong (Student ID: 60894001, Role D) · 2026-11-22
