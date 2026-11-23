# AGENTS.md

AGENTS.md is the single entry point for the AI coding agent. Before any coding
task, read this file, then follow the reading order below.

## Build target

- CS5351 project under `src/`; tests under `test/offline/` and `test/live/`.
- Python 3.11+; dependencies per `pyproject.toml` / `requirements.txt`.
- Code baseline: the `baseline-v0` tag = commit `b5d2f67` ("import upstream
  `9fa1196`, migrate to src layout"). Current main HEAD is `bebc576` (a later
  `.DS_Store` cleanup commit). Upstream TradingAgents import: `9fa1196`, tag
  `baseline-v0`.
- All new content in English.

## Reading order

Read these in order. Check which files exist; any missing file is marked
"(planned, owner: X)" and must never be presented as existing.

1. `AGENTS.md` (this file) — task scope, permissions, and startup gate.
2. `Prompt.md` — approval gate, read at planning-start. (exists, owner: B)
3. Task-relevant architecture: `architecture-blueprint.md` (planned, owner: C)
   and the governing ADR for the task (see task-specific reads below).
4. Requirements and invariants: `docs/req/requirements.yaml` (exists, owner: A)
   and `docs/architecture/invariants.md` — exists (owner: D).
5. Interface contracts under `docs/contracts/` (per-file status below).
6. Traceability and verification: `docs/architecture/trace-matrix.md` (planned,
   owner: A), `docs/code-governance/structural-constraints.md` — exists
   (owner: D), and `docs/code-governance/verification-constraints.md` — exists
   (owner: D).

Also read `docs/architecture/adr/001-adaptive-collaboration.md` (planned,
owner: C) when the task touches adaptive collaboration.

### Task-specific required reads

- C budget/recovery work: `docs/architecture/adr/004-budget-and-resume.md`
  (exists, owner: C) and `docs/contracts/execution-budget.md` (exists,
  owner: C).
- D deterministic boundary work: `docs/architecture/adr/005-deterministic-guard.md`
  (exists, owner: D) and `docs/contracts/validation-decision.md` (exists,
  owner: D).

Missing or conflicting required documents: stop the affected implementation and
report the missing items. Read-only exploration and personal drafts may
continue.

## Independent exploration and requirements review

- Members may discuss ideas with the agent, read permitted source, analyze
  architecture, compare alternatives, and explore candidate requirements
  without prior approval.
- Personal notes/drafts are writable ONLY under `docs/plans/<member>/`. They
  are proposals, never approved shared specifications.
- Discussion, notes, and TODOs do not constitute approval.
- Implementation requires approved scope plus the execution-plan approval gate
  in `Prompt.md`. The agent must not commit, push, open PRs, or merge without
  explicit human authorization.

## Readable / modifiable / frozen

All paths are repository-root-relative. Person-to-task assignment is managed by
the team separately and rotates per course policy; permissions are defined by
module, not by person. Default deny: the coding agent may edit only the paths
allowed below, and only under an approved execution plan.

### Three permission tiers

| Tier | Paths (repo-root-relative) | Rule |
| --- | --- | --- |
| Tier 1 — normally editable within an approved plan scope | Functional module whitelist under `src/tradingagents/` (see ownership below); new module `src/tradingagents/execution_policy.py` (owner: C); `test/offline/`; `test/fixtures/`; `docs/plans/<member>/` | Editable only within an approved plan scope. |
| Tier 2 — protected (approval required) | `src/tradingagents/graph/setup.py`, `src/tradingagents/graph/conditional_logic.py`, `src/tradingagents/graph/trading_graph.py`, `src/tradingagents/agents/state.py`, `src/tradingagents/default_config.py` (owner: C); `src/tradingagents/agents/schemas.py` (owner: B) | Editable only after an ADR covering the change plus explicit human approval; the owner integrates the change. |
| Tier 3 — always human-maintained | `.opencode/`, `.agent/`, `transcripts/` (agent never writes); `.env` (never read or committed) | Agent never writes; humans maintain. |

### Tier 1 functional module ownership

- C: the rest of `src/tradingagents/graph/` (excluding the protected integration
  files above), and the new module `src/tradingagents/execution_policy.py`.
- B: `src/tradingagents/agents/researchers/`,
  `src/tradingagents/agents/managers/research_manager.py`,
  `src/tradingagents/review.py`, `src/tradingagents/context_builder.py`.
- D: `src/tradingagents/constraints.py`,
  `src/tradingagents/agents/managers/portfolio_manager.py`,
  `src/tradingagents/agents/risk_mgmt/`, `src/tradingagents/agents/trader/`,
  `src/tradingagents/portfolio.py`, and their tests.
- A: `src/tradingagents/evidence.py`, `src/tradingagents/dataflows/`,
  `src/tradingagents/agents/analysts/`, `src/tradingagents/memory/`, and
  `docs/req/`.
- E: `src/tradingagents/run_recorder.py`, `src/tradingagents/reporting.py`,
  `src/tradingagents/report_html.py`, `src/tradingagents/backtest.py`,
  `src/tradingagents/llm_clients/`, `src/cli/`, and `.github/`.
- Other `src/` paths: role-owned only.

### Test boundaries

- Existing `tests/` is included in regression.
- New offline cases live under `test/offline/`; fixtures live under
  `test/fixtures/`.
- `test/` is role-owned; tests come before implementation; never weaken tests.

### Shared docs, personal notes, and overlap rule

- `docs/` shared specifications: write only with human approval.
- `docs/plans/<member>/`: that member's personal notes, freely writable.
- Overlap rule: most-restrictive wins. Protected and human-only rules override
  any general whitelist; explicit per-file rules override directory rules; no
  broad directory rule overrides a protection rule.

### Config loading: enforced limits vs policy source

- `opencode.jsonc` at the repository root (owner: E) is the enforced live config
  that actually enforces read/write limits. It is maintained by E and is not
  present in this checkout until E supplies it.
- `.opencode/permissions.jsonc` is the course POLICY SOURCE and is NOT
  auto-loaded by OpenCode.
- The two must stay in sync (`check_permission_sync`).

## Module organization

One architectural element per module. Names must match the ownership map above
and `architecture-blueprint.md`.

## Integration contracts

Contracts under `docs/contracts/` (status verified against tree, 2026-11-23):

- `docs/contracts/evidence.md` — (exists, owner: A)
- `docs/contracts/review-context.md` — (exists, owner: B)
- `docs/contracts/execution-budget.md` — (exists, owner: C)
- `docs/contracts/validation-decision.md` — (exists, owner: D)
- `docs/contracts/run-event.md` — (exists, owner: E)

## Verification requirements

- Every fit criterion has at least one test.
- Every invariant has at least one negative test that fails when violated. (See
  `docs/architecture/invariants.md` — exists, and
  `docs/architecture/adr/005-deterministic-guard.md` — exists; ADR-005
  additionally governs the deterministic guard and fail-closed verdict
  behavior.)
- Every test references its requirement/invariant ID.
- Every round runs all prior suites with zero regressions.
- Safety-critical changes require an ADR plus human approval.

## Stop rule

Before feature implementation, shared docs (`docs/approvals/`) must show
independent human approval of the PLAN VERSION, TEST VERSION, and MODIFICATION
SCOPE. Writing tests-for-review is allowed (it produces the red run); starting
feature implementation requires approved tests. Protected changes additionally
require an ADR covering the change plus explicit authorization. Approvals are
recorded in `docs/approvals/` by humans (approver, time, plan/test version,
scope); agents never sign approvals.

Re-approval triggers: work exceeds the approved scope; an approved contract is
changed; an existing safety boundary is affected. On any trigger, pause the
affected implementation, report the change and pending items, and obtain
approval before continuing. This gate does not apply to independent exploration
or personal notes.

## Root governance ownership

- `AGENTS.md` — owner: D
- `Prompt.md` — owner: B
- `architecture-blueprint.md` — owner: C
- `Report.md` — owner: E (integrates)

All changes to these files require human approval.
