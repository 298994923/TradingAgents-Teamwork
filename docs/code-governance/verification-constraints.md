# Verification Constraints

Status: Draft for human review  
Date: 2026-11-21  
Maintainer: safety-guard module maintainer  
Reviewer: human reviewer  
Related: `AGENTS.md`, `docs/code-governance/structural-constraints.md`,
`docs/architecture/invariants.md`,
`docs/architecture/adr/005-deterministic-guard.md`,
`docs/plans/D/requirements-pack.yaml`, `test/fixtures/safety_cases.json`

## Purpose and scope

This document records the verification constraints for the safety-guard work.
It defines what must be tested, how each test is traced to a requirement or
invariant, which tiers the suite is organized into, and the gate that governs
when implementation may begin. It is a governance specification; it does not
itself add or modify tests.

## Rule 1 — Every fit criterion has at least one test

Every fit criterion under `REQ-D-001` through `REQ-D-013` has at least one test.
The table maps each requirement to its governing invariants and the test
file(s) that implement or are planned to implement it. Files marked "planned"
are the ADR-005 targets and do not yet exist; the current edge stub lives in
`test/offline/test_constraints.py` and `test/offline/test_safety_boundary.py`.

| Requirement | Governing INV(s) | Test file(s) |
|---|---|---|
| REQ-D-001 | INV-D4, INV-D5, INV-D6, INV-D7 | `test/offline/test_constraints.py` (`test_guard_result_shape_and_positive_executable`) |
| REQ-D-002 | INV-D1 | `test/offline/test_constraints.py` (`test_inv_d1_position_cap`); planned `test_constraints_position_cap.py` |
| REQ-D-003 | INV-D2 | `test/offline/test_constraints.py` (`test_inv_d2_forbidden_tickers`); planned `test_constraints_forbidden.py` |
| REQ-D-004 | INV-D3 | `test/offline/test_constraints.py` (`test_inv_d3_rating_domain`); planned `test_constraints_rating.py` |
| REQ-D-005 | INV-D4 | `test/offline/test_constraints.py` (`test_inv_d4_review_terminal`), `test/offline/test_safety_boundary.py` (`test_review_is_non_executable_at_both_gates`); planned `test_constraints_review.py` |
| REQ-D-006 | INV-D5 | `test/offline/test_constraints.py` (`test_inv_d5_fail_closed`); planned `test_constraints_fail_closed.py` |
| REQ-D-007 | INV-D6 | `test/offline/test_constraints.py` (`test_inv_d6_dual_gate`), `test/offline/test_safety_boundary.py` (`test_dual_gate_trader_pass_then_pm_rating_block`, `test_dual_gate_trader_pass_then_pm_cap_block`, `test_missing_gate_is_block`); planned `test_constraints_dual_gate.py` |
| REQ-D-008 | INV-D7 | `test/offline/test_constraints.py` (`test_inv_d7_authority`, `test_verdict_domain`), `test/offline/test_safety_boundary.py` (`test_verdict_lattice_is_monotonic`, `test_block_survives_llm_claiming_pass`, `test_block_survives_later_valid_looking_decision`); planned `test_constraints_authority.py` |
| REQ-D-009 | INV-D8 | `test/offline/test_constraints.py` (`test_inv_d8_unknown_position`), `test/offline/test_safety_boundary.py` (`test_absent_context_is_review_not_flat`, `test_explicit_empty_positions_are_flat`, `test_unknown_nav_is_review_not_zero`, `test_malformed_portfolio_is_block`); planned `test_constraints_unknown_position.py` |
| REQ-D-010 | INV-D1, INV-D2, INV-D5, INV-D6, INV-D7, INV-D8 | planned `test_constraints_audit.py` |
| REQ-D-011 | INV-D1..INV-D8 | `pytest --collect-only -q test/offline/test_constraints*.py` plus traceability review |
| REQ-D-012 | INV-D1, INV-D2, INV-D5 | `test/offline/test_safety_boundary.py` (`test_invalid_config_blocks_before_any_decision`); planned `test_constraints_config.py` |
| REQ-D-013 | INV-D1, INV-D2, INV-D3, INV-D5, INV-D6, INV-D7, INV-D8 | `test/offline/test_constraints.py` (`test_guard_purity_no_network_io`), `test/offline/test_safety_boundary.py` (`test_determinism_100_identical_runs`); planned `test_constraints_determinism.py` |

## Rule 2 — Every invariant has a negative test that fails on violation

Every invariant `INV-D1` through `INV-D8` has at least one **negative** test
that fails if the invariant is removed or violated. Positive and boundary cases
do not satisfy this rule on their own. The negative fixtures are defined in
`test/fixtures/safety_cases.json` and exercised by the parametrized
`test_inv_d*` functions in `test/offline/test_constraints.py`.

| Invariant | Negative fixture ID(s) | Asserting test |
|---|---|---|
| INV-D1 | `d1-cap-plus-one-unit`, `d1-post-trade-holding-plus-delta`, `d1-existing-oversized-small-delta`, `d1-short-gross-abs-over-cap`, `d1-missing-nav` | `test_inv_d1_position_cap`, `test_determinism_100_identical_runs` |
| INV-D2 | `d2-forbidden-buy`, `d2-forbidden-add`, `d2-forbidden-new-short`, `d2-forbidden-normalized-ticker`, `d2-malformed-ticker` | `test_inv_d2_forbidden_tickers` |
| INV-D3 | `d3-strong-buy-alias`, `d3-empty-rating`, `d3-numeric-rating`, `d3-trader-five-tier-invalid`, `d3-review-sentinel` | `test_inv_d3_rating_domain` |
| INV-D4 | `d4-review-trader-terminal`, `d4-review-pm-terminal` | `test_inv_d4_review_terminal`, `test_review_is_non_executable_at_both_gates` |
| INV-D5 | `d5-missing-required-action`, `d5-null-delta`, `d5-nan-delta`, `d5-infinity-price`, `d5-wrong-type-delta`, `d5-modeled-unknown-not-block` | `test_inv_d5_fail_closed` |
| INV-D6 | `d6-dual-gate-pm-invalid-rating`, `d6-dual-gate-pm-cap-violation`, `d6-gate-missing` | `test_inv_d6_dual_gate`, `test_dual_gate_trader_pass_then_pm_rating_block`, `test_dual_gate_trader_pass_then_pm_cap_block`, `test_missing_gate_is_block` |
| INV-D7 | `d7-block-llm-claim-pass`, `d7-block-regenerated-answer`, `d7-lattice-block-over-pass`, `d7-lattice-review-over-pass` | `test_inv_d7_authority`, `test_block_survives_llm_claiming_pass`, `test_block_survives_later_valid_looking_decision`, `test_verdict_lattice_is_monotonic` |
| INV-D8 | `d8-absent-context`, `d8-absent-context-zero-delta`, `d8-unknown-nav`, `d8-malformed-portfolio-nav`, `d8-malformed-portfolio-positions`, `d8-unknown-ticker-row`, `d8-unknown-quantity`, `d8-malformed-position-quantity` | `test_inv_d8_unknown_position`, `test_absent_context_is_review_not_flat`, `test_unknown_nav_is_review_not_zero`, `test_malformed_portfolio_is_block` |

Each negative test asserts the failure action, not only the verdict: it checks
the verdict, the reason code, and that `executable is False`.

## Rule 3 — Every test cites its requirement/invariant ID

Every test cites the requirement or invariant ID(s) it verifies, in its
docstring or marker, in the form `INV-Dx / REQ-D-xxx`. This matches the existing
convention, for example `"""INV-D1 / REQ-D-002: cap and NAV handling."""`. A
test without a cited ID is nonconforming. New tests must continue this
convention and must be added under `test/offline/`.

## Three verification tiers

### Structural tier

Verifies the constraints in
`docs/code-governance/structural-constraints.md`:

- Each architectural element is one module, and module names match `AGENTS.md`.
- The baseline is extended, not replaced.
- Every module and public function cites its ADR/INV ID.
- The authority boundary holds: LLM advisory, deterministic guard
  authoritative.
- Guard purity: no LLM, network, or order I/O inside `constraints.py`.
- Protected integration files are unmodified without an ADR plus human
  approval.

### Regression tier

- Every round runs all prior suites and reports **zero regressions**.
- Tests are never weakened, skipped, or deleted to make CI pass.
- The suite is compared against the baseline commit
  `bebc5762f41abb5affc63a8cf9755d182f99df70`; a new failure is a regression even
  if the change is unrelated.
- Expected-failure or xfail markers may not be used to mask a violated
  invariant.

### Behavioral tier

For each safety case, the behavioral tier asserts the concrete observable
outcome:

- The **verdict** equals the expected verdict (`PASS` / `REVIEW` / `BLOCK`).
- The **reason code** equals the expected reason code (for example
  `CAP_EXCEEDED`, `FORBIDDEN_TICKER`, `OVERRIDE_REJECTED`).
- The **executable** flag matches the expectation: only `PASS` may be
  executable; `REVIEW` and `BLOCK` are non-executable.
- Any `expected_details` are asserted (for example
  `override_rejected: true`).
- **100-run determinism**: identical input yields identical verdict and reason
  code across 100 repeated runs (REQ-D-013, ADR-005 TBD-D-22). This is exercised
  by `test_determinism_100_identical_runs`.

The shared `_assert_case` helper in `test/offline/test_constraints.py` is the
canonical behavioral check and must remain the reference for new cases.

## Reproduction command

Run the offline suite from the repository root:

```sh
PYTHONPATH=src python3 -m pytest test/offline -v
```

## Red-then-green gate

- Tests are written and human-approved **before** implementation begins. The
  approved tests define the expected behavior and are the contract that
  implementation must satisfy.
- The suite starts **red**: the current guard is a naive stub, so the negative
  and boundary cases from `test/fixtures/safety_cases.json` fail until the real
  checks land. The existing red baseline is recorded in
  `docs/plans/D/red-run-01.txt`.
- Implementation proceeds to **green**: the checks are added until every
  approved test passes, with no test weakening.
- A safety-critical change requires an ADR plus explicit human approval before
  it is implemented.
- If approved behavior changes beyond the approved test set, obtain re-approval
  before implementation.

## Traceability

- Invariants: `docs/architecture/invariants.md` (INV-D1 through INV-D8).
- Architecture decision: `docs/architecture/adr/005-deterministic-guard.md`.
- Requirements: `docs/plans/D/requirements-pack.yaml` (REQ-D-001 through
  REQ-D-013).
- Fixtures: `test/fixtures/safety_cases.json`.
- Structural rules: `docs/code-governance/structural-constraints.md`.
