# D → C Reply: Repository AGENTS.md Governance Review

- Author: D (AGENTS.md owner / safety-guard module maintainer)
- Re: C-to-D-repository-governance-review (C verdict: CHANGES REQUIRED)
- D accepts CHANGES REQUIRED and will revise AGENTS.md, then submit for C re-review.
- Status: D's reply draft — to be verified and signed by D.

---

## 1. Whitelist and protected zones

### Config loading: rule text vs enforced limits
- OpenCode loads the project config from the repo-root `opencode.jsonc` (E-owned) — this is
  what actually enforces read/write limits. `.opencode/permissions.jsonc` is the course POLICY
  SOURCE and is NOT auto-loaded. The two must stay in sync (check_permission_sync).
- Startup directory: repository root. Target repo version: D branch d-safety-guard (latest
  commit includes AGENTS.md, invariants.md, ADR-005, permissions source, covenant).
- D distinguishes rule text (policy source) from enforced tool limits (opencode.jsonc) and will
  provide the actual config path + verification results (below).

### Three permission tiers (access table restructured)
- Tier 1 — normally editable (within an approved plan scope): the module whitelist by function
  under src/tradingagents/ (per ownership), test/offline/, test/fixtures/, docs/plans/<member>/.
- Tier 2 — editable only after approval (protected): graph/setup.py, graph/conditional_logic.py,
  graph/trading_graph.py, agents/state.py, default_config.py (owner C); agents/schemas.py
  (owner B). Each edit requires an ADR covering the change + explicit human approval, and is
  integrated by the owner.
- Tier 3 — always human-maintained: .opencode/, .agent/, transcripts/ (agent never writes);
  .env never read or committed.
- execution_policy.py: confirmed addable within C's approved scope (Tier 1, C-owned new module).
- Rule overlap: most-restrictive wins — protected / human-only rules override any general
  whitelist; explicit per-file rules override directory rules.

### Paths and test boundaries
- All paths repo-root-relative (avoid source-dir whitelist matching the wrong location).
- Existing tests/ included in regression; new offline cases in test/offline/.
- Separate write permissions: tests (role-owned, tests-before-implementation), approved plan
  docs (docs/plans/<member>/ personal), shared specs (docs/ human-approval). No broad directory
  rule overrides a protection rule.

### Permission verification (ACTION, with E)
D + E will run allow/deny tests against the real opencode.jsonc and record results:
- an approved path is editable;
- a protected file (e.g. graph/setup.py) is NOT editable without approval;
- .env read is denied;
- covered via BOTH the edit tool and an alternative shell path (e.g. attempt write to a
  protected file, attempt to read .env); temporary placeholder files used to verify deny rules.
Results recorded and attached for C re-review. (Not assumed from permissions.jsonc text.)

---

## 2. Reading order

- Revised order: AGENTS.md (task scope / permissions / startup gate) → Prompt.md (approval gate,
  moved to planning-start) → task-relevant Blueprint + ADR → requirements + invariants →
  interface contracts → traceability + verification constraints.
- Task-specific required reads: C budget/recovery → docs/architecture/adr/004-budget-and-resume.md
  + docs/contracts/execution-budget.md; D deterministic boundary → ADR-005 +
  docs/contracts/validation-decision.md.
- invariants.md existence: EXISTS in D branch d-safety-guard (created and committed). C's local
  copy at bebc576 predates D's commits; C should fetch/sync d-safety-guard. Source: D branch.
- Baseline correction: baseline-v0 tag = b5d2f67 (upstream import + src migration); bebc576 is a
  later .DS_Store cleanup commit. AGENTS.md will state baseline-v0 (b5d2f67) as the code baseline
  and bebc576 as current main HEAD.
- Missing/conflicting required docs: stop the affected implementation and report the missing
  items; allowed read-only exploration and personal drafts may continue.

---

## 3. Stop and re-approval

- Before feature implementation, shared docs (docs/approvals/) must show independent human
  approval of the PLAN VERSION, TEST VERSION, and MODIFICATION SCOPE. Protected changes also
  require an ADR covering the change + explicit authorization.
- Stop clause updated to require BOTH plan approval AND independent test approval (gate 1).
  Distinguish writing tests-for-review (allowed; produces the red run) from starting feature
  implementation (requires approved tests). Wording/recording consistent with Prompt.md and
  docs/code-governance/verification-constraints.md.
- Re-approval triggers: work exceeds the approved scope; an approved contract is changed; an
  existing safety boundary is affected → pause the affected implementation, report the change
  and pending items, obtain approval before continuing.
- Approval recording: docs/approvals/ (human-only), each entry = approver + time + plan/test
  version (commit) + scope; reviewer conclusions in docs/review-memo.md.
- Revised shared-doc location for C re-review: repo-root AGENTS.md on D branch d-safety-guard
  (plus the permission-verification results).

---

## Summary of D commitments
1. Restructure access table into three tiers; add execution_policy.py; repo-root-relative paths;
   most-restrictive-wins overlap rule.
2. Run real allow/deny permission verification with E (edit tool + shell), record results.
3. Move Prompt.md to planning-start; add task-specific ADR/contract reads; correct baseline
   (baseline-v0=b5d2f67); note invariants.md exists on D branch.
4. Stop clause requires plan + independent test approval (version + scope); define re-approval
   triggers; record approvals in docs/approvals/.
5. Submit revised AGENTS.md + verification results for C re-review.
