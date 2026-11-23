# Structural Constraints

Status: Draft for human review  
Date: 2026-11-21  
Maintainer: safety-guard module maintainer  
Reviewer: human reviewer  
Related: `AGENTS.md`, `docs/architecture/invariants.md`,
`docs/architecture/adr/005-deterministic-guard.md`,
`docs/code-governance/verification-constraints.md`,
`docs/plans/D/requirements-pack.yaml`

## Purpose and scope

This document records the structural (module-organization) constraints for the
CS5351 project under `src/tradingagents/`. It governs how source modules are
organized, extended, and traced to the architecture decisions and safety
invariants. It is a governance specification; it does not itself implement or
describe implementation code.

Paths are relative to `src/tradingagents/` unless stated otherwise. Names in this
document must match the module names in `AGENTS.md` and in
`architecture-blueprint.md` (planned).

## One architectural element per module

Each module owns exactly one architectural element. Module names match the
names used in `AGENTS.md`; a new element is introduced as a new module, not by
overloading an existing one.

| Architectural element | Module path(s) | Responsibility |
|---|---|---|
| Graph orchestration | `graph/` (excluding the protected integration files below) | Assemble and drive the multi-agent workflow. |
| Agent schemas, research, review, and context | `agents/researchers/`, `agents/managers/research_manager.py`, `review.py`, `context_builder.py` | Produce advisory research, review, and context artifacts. |
| Safety guard and portfolio/risk/trader | `constraints.py`, `agents/managers/portfolio_manager.py`, `agents/risk_mgmt/`, `agents/trader/`, `portfolio.py` | Own the deterministic safety verdict and the portfolio/risk/trader decision path. |
| Evidence, data, memory, and analysts | `evidence.py`, `dataflows/`, `agents/analysts/`, `memory/` | Supply evidence, market data, analyst output, and memory. |
| Recording, reporting, backtest, LLM clients, CLI, and CI | `run_recorder.py`, `reporting.py`, `report_html.py`, `backtest.py`, `llm_clients/`, `src/cli/`, `.github/` | Record runs, render reports, backtest, wrap LLM clients, and provide CLI/CI. |

The safety guard is a single architectural element: `constraints.py` owns the
deterministic verdict, and no other module may re-implement or bypass it.

## Extend the upstream baseline; never replace it

- The repository baseline is commit `bebc5762f41abb5affc63a8cf9755d182f99df70`
  (upstream TradingAgents import `9fa1196`, tag `baseline-v0`).
- New work extends the baseline: new modules and new functions are added
  alongside existing modules.
- Existing modules must not be renamed, deleted, or rewritten wholesale to make
  room for new behavior. Behavior changes to an existing module are localized
  edits that preserve that module's single architectural element.
- A change that would require replacing a baseline module requires an ADR plus
  explicit human approval before it is made.

## Every module and function references its ADR/INV ID

Every module and every public function cites the ADR and invariant IDs that
govern it, in the module docstring or function docstring. A module or function
without a governing ID is nonconforming and is caught by the structural tier in
`docs/code-governance/verification-constraints.md`.

| Element / module | Governing ADR | Governing INV / REQ |
|---|---|---|
| `constraints.py` (guard entry points: `validate`, `validate_position_cap`, `validate_forbidden_tickers`, `validate_rating`, `validate_required_fields`, `validate_trader_proposal`, `validate_final_decision`, `resolve_position_state`, `merge_verdicts`, `finalize_verdict`, `is_executable`) | ADR-005 | INV-D1..INV-D8; REQ-D-001..REQ-D-013 |
| `portfolio.py` (portfolio states: absent / explicit empty / unknown / malformed) | ADR-005 | INV-D1, INV-D8; REQ-D-002, REQ-D-009 |
| `agents/trader/` (Trader proposal and first gate) | ADR-005 | INV-D3, INV-D4, INV-D6; REQ-D-004, REQ-D-005, REQ-D-007 |
| `agents/managers/portfolio_manager.py` (final decision and second gate) | ADR-005 | INV-D3, INV-D4, INV-D6; REQ-D-004, REQ-D-005, REQ-D-007 |
| `agents/managers/research_manager.py` (recommendation domain) | ADR-005 | INV-D3; REQ-D-004 |
| `agents/risk_mgmt/` (risk debate input to decisions) | ADR-005 | INV-D6, INV-D7; REQ-D-007, REQ-D-008 |
| `agents/researchers/`, `review.py`, `context_builder.py` | _(advisory; cite the INV/REQ they feed)_ | INV-D3, INV-D6, INV-D7 where they feed a graded decision |
| `graph/`, `evidence.py`, `dataflows/`, `agents/analysts/`, `memory/`, `run_recorder.py`, `reporting.py`, `report_html.py`, `backtest.py`, `llm_clients/`, `src/cli/`, `.github/` | _(cite the INV/REQ they affect)_ | Must not bypass or weaken INV-D1..INV-D8 |

A baseline module that is untouched by the safety work cites the ID it already
satisfies; it is not exempt from having a traceable ID.

## Authority boundary

- The LLM agents — analysts, researchers, risk debaters, the Trader, and the
  Portfolio Manager — are **advisory**. Their output is reasoned but
  nondeterministic and prompt-injectable.
- The deterministic guard in `constraints.py` is **authoritative**. It returns
  exactly one of `PASS`, `REVIEW`, or `BLOCK`, with the verdict lattice
  `BLOCK > REVIEW > PASS`.
- Merging takes the maximum severity and is monotonic: a verdict is never
  lowered by a later check, an LLM message, a debate argument, a regenerated
  answer, or a prompt injection.
- No LLM output can change a guard verdict. `BLOCK` has no in-system override;
  exceptions require an out-of-band signed human process and a new or amended
  ADR.

This boundary is binding on every module: no decision path may emit an
actionable trade artifact without a guard verdict. See ADR-005, INV-D7, and
REQ-D-008.

## Guard purity

`constraints.py` is a pure deterministic computation:

- It performs **no LLM, network, or order I/O**.
- It uses deterministic decimal arithmetic with a relative epsilon of `1e-9`; no
  larger policy buffer is permitted.
- It has no live FX dependency; a currency mismatch produces `REVIEW` rather
  than a nondeterministic conversion.
- Identical inputs produce identical verdicts and reason codes across repeated
  runs.

Purity is verified by `test_guard_purity_no_network_io` (REQ-D-013) and the
100-run determinism check (REQ-D-013, ADR-005 TBD-D-22).

## Protected integration files

The following protected integration files require an **ADR plus explicit human
approval** before any edit:

- `graph/setup.py`
- `graph/conditional_logic.py`
- `graph/trading_graph.py`
- `agents/state.py`
- `default_config.py`
- `agents/schemas.py`

All other paths are default-deny: the coding agent edits only the whitelisted
paths and only under an approved execution plan. `.opencode/`, `.agent/`,
`.env`, and `transcripts/` are human-only as defined in `AGENTS.md`.

## Enforcement

- Structural conformance is checked by the structural tier described in
  `docs/code-governance/verification-constraints.md`.
- Changes to this document and to shared specifications under `docs/` require
  human approval.
- Safety-critical structural changes require an ADR plus human approval before
  implementation.
