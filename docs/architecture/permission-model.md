# Permission Model

Status: Draft for human review  
Date: 2026-11-21  
Owner: D  
Reviewer: B  
Related: `AGENTS.md`, `.opencode/rules.md`, `.opencode/permissions.jsonc`,
`docs/architecture/adr/005-deterministic-guard.md`

## Purpose and scope

This document defines the module-based permission model for the CS5351 project.
Permissions are assigned by module, not by person; person-to-task assignment is
managed by the team separately and rotates per course policy. It mirrors the
access table in the current `AGENTS.md` and records the relationship between the
course policy source and the enforced live configuration.

The model is default deny. The coding agent may read or edit only the paths
allowed below, and only under an approved execution plan. Human-maintained paths
are outside the agent's write scope entirely.

Source anchors: CRS D2 item 6 (permission model default-deny whitelist),
`.opencode/rules.md` rules 1, 2, 8, and 9.

## Principals

- **Human** — the maintainer and approver. Humans maintain Tier 3 paths, sign
  approvals, and are the only principal allowed to change protected integration
  files or the permission configuration. Agents never sign approvals.
- **Coding agent (generic)** — any AI coding agent acting in this repository.
  It is role-agnostic: the same default-deny rules apply regardless of which
  team member the agent is assisting. It may act only within approved plan scope
  and only on Tier 1 whitelisted paths.

Default deny applies to both principals' repositories access except where a
whitelist, protection rule, or human-only rule explicitly states otherwise. The
most-restrictive applicable rule wins.

## Readable / modifiable / frozen

All paths are repository-root-relative. Default deny: the coding agent may edit
only the paths allowed below, and only under an approved execution plan.

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

### Additional hard denies

- `.env` is never read and never committed.
- `transcripts/` is human-only; the agent never writes to it.
- `.git/**`, `.venv/**`, and `secrets/**` are denied, per the course policy
  source. Secrets, tokens, and private keys are never read (`.opencode/rules.md`
  rule 2).

## Config loading: enforced limits vs policy source

- `opencode.jsonc` at the repository root (owner: E) is the enforced live config
  that actually enforces read/write limits. It is maintained by E and is not
  present in this checkout until E supplies it (planned, absent). It must never
  be presented as existing until it is committed.
- `.opencode/permissions.jsonc` is the course POLICY SOURCE and is NOT
  auto-loaded by OpenCode.
- The two must stay in sync (`check_permission_sync`). Any change to one
  requires the corresponding change to the other plus human approval.

### Current policy-source snapshot

The checked-in `.opencode/permissions.jsonc` currently states:

| Key | Entries |
| --- | --- |
| `default` | `deny` |
| `allow` | `src/tradingagents/constraints.py`, `src/tradingagents/agents/managers/portfolio_manager.py`, `src/tradingagents/agents/risk_mgmt/**`, `src/tradingagents/agents/trader/**`, `src/tradingagents/portfolio.py`, `test/offline/**`, `test/fixtures/**` |
| `protected` | `src/tradingagents/graph/setup.py`, `src/tradingagents/graph/conditional_logic.py`, `src/tradingagents/graph/trading_graph.py`, `src/tradingagents/agents/state.py`, `src/tradingagents/default_config.py`, `src/tradingagents/agents/schemas.py` |
| `deny` | `**/.env`, `**/.git/**`, `**/.venv/**`, `**/secrets/**` |
| `human_only` | `.opencode/**`, `.agent/**`, `transcripts/**` |

## check_permission_sync item (open)

Flagged discrepancy, recorded here without altering either file:

- The concrete `allow` globs in `.opencode/permissions.jsonc` are **D-scoped**
  (they list only D's modules plus `test/offline/**` and `test/fixtures/**`),
  whereas the current `AGENTS.md` three-tier table and Tier 1 ownership map define
  Tier 1 modules for **all roles** (C, B, D, A, E).
- The policy source also omits Tier 1 paths present in `AGENTS.md`, such as
  `docs/plans/<member>/`, and does not enumerate non-D module globs.
- This discrepancy is a `check_permission_sync` item to be reconciled with E
  together with the live `opencode.jsonc`. Until reconciled, the most-restrictive
  rule applies (default deny plus the explicit protection and human-only rules).
- Owner: E (live config) with D (this document). Status: pending. Neither
  `AGENTS.md` nor `.opencode/permissions.jsonc` is edited by this document.

## Verification ritual

The permission model must be validated by allow/deny probes. Each probe is run
through **both** the edit tool and the shell, so that tool-level and
process-level enforcement are checked independently. Results are recorded below;
they are pending until the live enforced config is supplied and the probes run
jointly with E.

| # | Probe | Method(s) | Expected | Observed | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Edit an approved Tier 1 path (for example a D-owned module or `test/offline/`) inside an approved plan scope | edit tool + shell | allow | not run | pending |
| 2 | Edit a protected Tier 2 path (for example `src/tradingagents/agents/schemas.py`) without approval | edit tool + shell | deny | not run | pending |
| 3 | Read `.env` | edit tool + shell | deny | not run | pending |
| 4 | Write a Tier 3 path (for example `.opencode/` or `transcripts/`) | edit tool + shell | deny | not run | pending |
| 5 | Read `.git/**`, `.venv/**`, or `secrets/**` | shell | deny | not run | pending |

Recording rules:

- A probe is only `pass` when both methods produce the expected result under the
  enforced live config.
- Any mismatch blocks release of the permission configuration and is reported to
  E and the human maintainer.
- The enforced live config (`opencode.jsonc`) is absent from this checkout, so
  all statuses remain `pending` and no enforcement is claimed.

## Change control

- Changes to this document are shared-specification changes requiring human
  approval.
- Changes to `.opencode/permissions.jsonc`, `.opencode/rules.md`, `AGENTS.md`, or
  the live `opencode.jsonc` are human-maintained and outside the agent's write
  scope.
- Protected changes additionally require an ADR covering the change plus explicit
  human authorization.

## References

- `AGENTS.md` — three permission tiers, ownership map, overlap rule, config note.
- `.opencode/rules.md` — always-on rules, including default deny and no
  self-approval.
- `.opencode/permissions.jsonc` — course policy source (not auto-loaded).
- `docs/architecture/adr/005-deterministic-guard.md` — authority model and
  protected integration constraints.
