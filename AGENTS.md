# AGENTS.md

AGENTS.md is the single entry point for the AI coding agent. Before any coding
task, read this file, then follow the reading order below.

## Build target

- CS5351 project under `src/`; tests under `test/offline/` and `test/live/`.
- Python 3.11+; dependencies per `pyproject.toml` / `requirements.txt`.
- Repository baseline commit: `bebc5762f41abb5affc63a8cf9755d182f99df70`
  (upstream TradingAgents import: `9fa1196`, tag `baseline-v0`).
- All new content in English.

## Reading order

Read these in order. Check which files exist; any missing file is marked
"(planned, owner: X)" and must never be presented as existing.

1. `architecture-blueprint.md` — (planned, owner: C)
2. `docs/architecture/adr/001-adaptive-collaboration.md` — (planned, owner: C)
3. `docs/architecture/invariants.md` — exists (owner: D)
4. `docs/architecture/trace-matrix.md` — (planned, owner: A)
5. `docs/req/requirements.yaml` — (planned, owner: A)
6. `docs/code-governance/structural-constraints.md` — (planned, owner: D)
7. `docs/code-governance/verification-constraints.md` — (planned, owner: D)
8. `Prompt.md` — (planned, owner: B)

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

Paths are relative to `src/tradingagents/` unless stated otherwise.

| Owner | Paths | Access |
| --- | --- | --- |
| C | `graph/setup.py`, `graph/conditional_logic.py`, `graph/trading_graph.py`, `agents/state.py`, `default_config.py` | Exclusive |
| C | rest of `graph/` | Maintains |
| B | `agents/schemas.py`, `agents/researchers/`, `agents/managers/research_manager.py`, `review.py`, `context_builder.py` | Exclusive |
| D | `constraints.py`, `agents/managers/portfolio_manager.py`, `agents/risk_mgmt/`, `agents/trader/`, `portfolio.py`, and their tests | May write |
| A | `evidence.py`, `dataflows/`, `agents/analysts/`, `memory/`, `docs/req/` | Owns |
| E | `run_recorder.py`, `reporting.py`, `report_html.py`, `backtest.py`, `llm_clients/`, `src/cli/`, `.github/` | Owns |

- Other `src/` paths: role-owned only.
- `test/`: role-owned; tests before implementation; never weaken tests.
- `docs/` shared specifications: write only with human approval.
- `docs/plans/<member>/`: that member's personal notes, freely writable.
- `.opencode/` and `.agent/`: human-only, agent never writes.
- `.env`: never read or commit.
- `transcripts/`: human-only; agents never write; humans export/annotate.

## Module organization

One architectural element per module. Names must match the ownership map above
and `architecture-blueprint.md`.

## Integration contracts

Five contracts under `docs/contracts/`, all "(planned, to be created by each
owner)":

- `docs/contracts/evidence.md` — (planned, owner: A)
- `docs/contracts/review-context.md` — (planned, owner: B)
- `docs/contracts/execution-budget.md` — (planned, owner: C)
- `docs/contracts/validation-decision.md` — (planned, owner: D)
- `docs/contracts/run-event.md` — (planned, owner: E)

## Verification requirements

- Every fit criterion has at least one test.
- Every invariant has at least one negative test that fails when violated. (See
  `docs/architecture/invariants.md` and
  `docs/architecture/adr/005-deterministic-guard.md`; ADR-005 additionally
  governs the deterministic guard and fail-closed verdict behavior.)
- Every test references its requirement/invariant ID.
- Every round runs all prior suites with zero regressions.
- Safety-critical changes require an ADR plus human approval.

## Stop rule

Before generating implementation code, produce an execution plan per
`Prompt.md` and wait for explicit human approval (`APPROVED`). If architecture
or contracts change beyond approved scope, obtain re-approval. This gate does
not apply to independent exploration or personal notes.

## Root governance ownership

- `AGENTS.md` — D
- `Prompt.md` — B
- `architecture-blueprint.md` — C
- `Report.md` — E integrates

All changes to these files require human approval.
