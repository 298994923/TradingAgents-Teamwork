# Safety Invariants

Status: Draft for human review (policy adopted 2026-11-21)  
Maintainer: safety-guard module maintainer  
Reviewer: human reviewer  
Related: `docs/architecture/adr/005-deterministic-guard.md`, `docs/plans/D/requirements-pack.yaml`

## Authority and scope

The AI agents are advisory. The deterministic guard in `constraints.py` is
authoritative. No LLM output, prompt, debate result, or generated explanation can
change a verdict produced by that guard.

This document defines the safety-guard module's hard invariants. Each invariant is a
specified design target for `constraints.py`, with target verification encoded by a
negative test. The offline suite lives in `test/offline/test_constraints.py` and
`test/offline/test_safety_boundary.py`; fixture IDs below refer to
`test/fixtures/safety_cases.json`.

## Source anchors

- **CRS §1 (Project Overview):** safety boundary / deterministic constraint.
- **CRS D2 item 3:** invariant register five elements.
- **CRS D2 item 6:** permission model default-deny whitelist.
- **CRS D3:** negative test per feature and safety-critical ADR plus human
  approval.
- **CRS D4:** every invariant has at least one negative test that fails on
  violation.
- **TP-§7:** team plan D tasks.

## Definitions

- **NAV**: cash plus the market value of every position at the analysis date, in
  the account currency. Unknown NAV is not zero; it is an explicitly modeled
  unknown and produces `REVIEW` when a cap check needs it.
- **Position cap**: 10% of NAV per instrument, measured as gross absolute
  post-trade exposure. Post-trade exposure is `abs(current quantity + proposed
  delta) * price`. Equality is allowed: `exposure <= cap`.
- **Numeric comparison**: with `cap = 10% of NAV` and `exposure = gross absolute
  post-trade exposure`, all arithmetic uses `Decimal`. Within-cap iff
  `exposure <= cap + cap * Decimal("1e-9")`; over-cap (`BLOCK` /
  `CAP_EXCEEDED`) iff `exposure > cap + cap * Decimal("1e-9")`. Equality is
  allowed, and no larger policy buffer is permitted.
- **Verdicts**: `PASS`, `REVIEW`, `BLOCK`.
- **Verdict lattice**: `BLOCK > REVIEW > PASS`. Merging two verdicts takes the
  higher severity. A verdict is monotonic and is never lowered once raised.
- **REVIEW**: a terminal, non-executable disposition for explicitly modeled
  unknown or insufficient information. There is no automatic retry.
- **BLOCK**: a hard, non-executable violation. There is no in-system override.
  Exceptions require an out-of-band signed human process and a new or amended
  ADR; an LLM can never issue one.
- **Execution path**: any actionable trade artifact, including a Buy/Sell
  instruction with non-zero sizing or quantity, and any future order-dispatch
  call. Reports, state logs, and audit records are not execution artifacts, but
  they must label `REVIEW` and `BLOCK` as non-executable.
- **Fail-closed**: a missing or malformed required field, schema failure, or
  parse failure produces `BLOCK`. Only explicitly modeled unknown states produce
  `REVIEW`. An unknown position is never treated as an empty position.
- **Failure action vocabulary**: set the verdict; emit a `REVIEW` disposition;
  suppress any actionable trade artifact; write a verdict record containing the
  reason code, checkpoint, observed value, allowed value, and inputs used.

## Invariant summary

| Invariant | Subject | Source requirement |
|---|---|---|
| INV-D1 | Position cap | REQ-D-002 |
| INV-D2 | Forbidden ticker list | REQ-D-003 |
| INV-D3 | Rating domain | REQ-D-004 |
| INV-D4 | REVIEW never executable | REQ-D-005 |
| INV-D5 | Fail-closed on missing/malformed fields | REQ-D-006 |
| INV-D6 | Validation after Trader and after PM | REQ-D-007 |
| INV-D7 | BLOCK not overridable by an LLM | REQ-D-008 |
| INV-D8 | Unknown position is not empty position | REQ-D-009 |

## INV-D1 — Position cap

- **Status:** specified design target — implementation pending gate-1 approval;
  current `constraints.py` is a naive stub (`validate()` always returns `PASS`),
  so this invariant is not yet enforced.
- **Statement:** For the analyzed instrument, gross absolute post-trade exposure
  (`abs(current quantity + proposed delta) * price`) must be at most 10% of NAV.
  Equality is allowed under the explicit Decimal tolerance: within-cap iff
  `exposure <= cap + cap * Decimal("1e-9")`; over-cap (`BLOCK` /
  `CAP_EXCEEDED`) iff `exposure > cap + cap * Decimal("1e-9")`. A missing or
  malformed field required to compute the cap
  is `BLOCK`; an explicitly modeled unknown NAV, price, quantity, or currency
  mismatch is `REVIEW`. An unknown position is never treated as zero.
- **Source requirement ID:** `REQ-D-002` (CRS §1; CRS D2 item 3; CRS D3; CRS D4; TP-§7).
- **Enforcing component:** `constraints.py::validate_position_cap`, called from
  the Trader gate and again from the final PM gate.
- **Verification method (negative test):**
  `test/offline/test_constraints.py::test_inv_d1_position_cap` (fixtures
  `d1-below-cap`, `d1-exact-cap`, `d1-cap-plus-epsilon`,
  `d1-cap-within-relative-tolerance`, `d1-cap-at-relative-tolerance-edge`,
  `d1-cap-just-over-relative-tolerance`, `d1-cap-plus-one-unit`,
  `d1-post-trade-holding-plus-delta`, `d1-existing-oversized-small-delta`,
  `d1-missing-nav`, `d1-short-gross-abs-over-cap`, `d1-short-within-cap`,
  `d1-currency-mismatch`) and
  `test/offline/test_constraints.py::test_inv_d1_over_cap_audit_details`
  (fixtures `d1-cap-plus-epsilon`, `d1-cap-plus-one-unit`,
  `d1-cap-just-over-relative-tolerance`, `d1-existing-oversized-small-delta`,
  `d1-short-gross-abs-over-cap`) cover post-trade exposure at cap plus one basis
  point and at cap plus one unit expecting `BLOCK`; exactly-at-cap expecting
  `PASS`; unknown NAV/quantity expecting `REVIEW`; malformed quantity expecting
  `BLOCK`; a short position and an alias ticker measured the same way; and a
  proposed delta that leaves an already-oversized holding above cap expecting
  `BLOCK`. `test/offline/test_constraints.py::test_guard_purity_no_network_io`
  uses inline fixtures only;
  `test/offline/test_safety_boundary.py::test_determinism_100_identical_runs`
  uses fixture `d13-determinism-cap-block-100-runs`; and
  `test/offline/test_safety_boundary.py::test_invalid_config_blocks_before_any_decision`
  uses fixture `d12-config-negative-cap`.
- **Concrete failure action:** set `BLOCK`; emit `REVIEW`; suppress the
  actionable trade artifact; write `CAP_EXCEEDED` with observed exposure, 10% NAV
  cap, NAV basis, post-trade quantity, and price. For modeled unknowns, set
  `REVIEW` with `POSITION_UNKNOWN` or `NAV_UNKNOWN` and still suppress the
  artifact.

## INV-D2 — Forbidden ticker list

- **Status:** specified design target — implementation pending gate-1 approval;
  current `constraints.py` is a naive stub (`validate()` always returns `PASS`),
  so this invariant is not yet enforced.
- **Statement:** An exposure-increasing action (Buy, add, or new short) on any
  ticker in the forbidden list must be blocked. Reductions and exits are allowed.
  The list is a static human-curated file. It is seeded with the single
  illustrative entry `DEMO-BAN`, clearly marked as an example for tests and
  demos; real entries are added only by a human. Matching uses the existing
  normalized ticker form, not raw strings.
- **Source requirement ID:** `REQ-D-003` (CRS §1; CRS D2 items 3 and 6; CRS D3; CRS D4; TP-§7).
- **Enforcing component:** `constraints.py::validate_forbidden_tickers`, called
  from the Trader gate and again from the final PM gate.
- **Verification method (negative test):**
  `test/offline/test_constraints.py::test_inv_d2_forbidden_tickers` (fixtures
  `d2-forbidden-buy`, `d2-forbidden-add`, `d2-forbidden-new-short`,
  `d2-forbidden-reduce`, `d2-forbidden-exit`,
  `d2-forbidden-normalized-ticker`, `d2-clean-ticker`, `d2-malformed-ticker`)
  and
  `test/offline/test_safety_boundary.py::test_invalid_config_blocks_before_any_decision`
  (fixture `d12-config-forbidden-not-list`) cover `DEMO-BAN` with a Buy/add/short
  expecting `BLOCK`; `DEMO-BAN` with a reduction or exit expecting `PASS` from
  this check; an alias spelling of `DEMO-BAN` expecting `BLOCK`; a valid ticker
  absent from the list passing this check; and an unnormalizable or malformed
  ticker field expecting `BLOCK`.
- **Concrete failure action:** set `BLOCK`; emit `REVIEW`; suppress the
  actionable trade artifact; write `FORBIDDEN_TICKER` with the normalized ticker,
  the matched list entry, and the proposed action. Log an attempted exit as
  `ALLOWED_EXIT` without changing the verdict.

## INV-D3 — Rating domain

- **Status:** specified design target — implementation pending gate-1 approval;
  current `constraints.py` is a naive stub (`validate()` always returns `PASS`),
  so this invariant is not yet enforced.
- **Statement:** Any emitted tradeable rating must be exactly one of `Buy`,
  `Overweight`, `Hold`, `Underweight`, or `Sell`, after case-insensitive
  trimming to the canonical form. No aliases such as "Strong Buy" are accepted.
  The Research Manager recommendation and the Portfolio Manager final rating use
  this 5-tier domain; the Trader action uses its separate 3-tier domain
  (`Buy`/`Hold`/`Sell`). `REVIEW` is the only allowed non-tier signal and is
  never a tradeable rating.
- **Source requirement ID:** `REQ-D-004` (CRS §1; CRS D2 item 3; CRS D3; CRS D4; TP-§7).
- **Enforcing component:** `constraints.py::validate_rating`, invoked on the
  Research Manager recommendation, the Trader action, and the final PM rating.
- **Verification method (negative test):**
  `test/offline/test_constraints.py::test_inv_d3_rating_domain` (fixtures
  `d3-pm-canonical-buy`, `d3-pm-canonical-overweight`,
  `d3-pm-canonical-hold`, `d3-pm-canonical-underweight`,
  `d3-pm-canonical-sell`, `d3-normalized-case-whitespace`,
  `d3-strong-buy-alias`, `d3-empty-rating`, `d3-numeric-rating`,
  `d3-trader-three-tier-buy`, `d3-trader-three-tier-hold`,
  `d3-trader-three-tier-sell`, `d3-trader-five-tier-invalid`,
  `d3-review-sentinel`) covers values such as `Strong Buy`, an empty string, a
  number, a translated value, and an unknown alias expecting `BLOCK`; lowercase
  or padded canonical values expecting `PASS`; and a decision that is explicitly
  the `REVIEW` sentinel expecting `REVIEW` and no tradeable rating.
- **Concrete failure action:** for a present value outside the allowed domain,
  set `BLOCK`; emit `REVIEW`; suppress the actionable trade artifact; write
  `INVALID_RATING` with the field, raw value, and allowed domain. For the
  explicit `REVIEW` sentinel, set terminal `REVIEW` with `RATING_UNREADABLE`.

## INV-D4 — REVIEW never enters the execution path

- **Status:** specified design target — implementation pending gate-1 approval;
  current `constraints.py` is a naive stub (`validate()` always returns `PASS`),
  so this invariant is not yet enforced.
- **Statement:** A `REVIEW` verdict is terminal and non-executable. It produces
  no actionable trade artifact, no order, and no retry. It may be recorded in the
  state log, report, and audit record only when clearly labelled as
  non-executable.
- **Source requirement ID:** `REQ-D-005` (CRS §1; CRS D2 item 3; CRS D3; CRS D4; TP-§7).
- **Enforcing component:** `constraints.py::finalize_verdict` and
  `constraints.py::is_executable`, called at the end of the Trader gate and the
  final PM gate.
- **Verification method (negative test):**
  `test/offline/test_constraints.py::test_inv_d4_review_terminal` (fixtures
  `d4-review-trader-terminal`, `d4-review-pm-terminal`) injects `REVIEW` into the
  Trader result and into the final PM result;
  `test/offline/test_constraints.py::test_guard_result_shape_and_positive_executable`
  uses inline fixtures only; and
  `test/offline/test_safety_boundary.py::test_review_is_non_executable_at_both_gates`
  uses inline fixtures `VALID_TRADER`, `VALID_PM`, and `KNOWN_BOOK` across stages
  `trader` and `pm`. These assert no actionable trade artifact is produced, no
  execution callback fires, no retry occurs, and the audit record still labels
  the disposition `REVIEW` and non-executable.
- **Concrete failure action:** keep `REVIEW`; emit a non-executable
  `REVIEW` disposition; suppress the actionable trade artifact; write
  `REVIEW_TERMINAL` with the source checkpoint and reason. If executable output
  is detected, raise `BLOCK` with `REVIEW_EXECUTION_LEAK` and suppress it.

## INV-D5 — Fail-closed on missing or malformed fields

- **Status:** specified design target — implementation pending gate-1 approval;
  current `constraints.py` is a naive stub (`validate()` always returns `PASS`),
  so this invariant is not yet enforced.
- **Statement:** A missing or malformed required field, or a schema or parse
  failure, produces `BLOCK` unless the field is an explicitly modeled unknown
  state, which produces `REVIEW`. The guard never fills a missing value with a
  default, never treats malformed data as absent, and never converts either into
  `PASS` or `Hold`.
- **Source requirement ID:** `REQ-D-006` (CRS §1; CRS D2 item 3; CRS D3; CRS D4; TP-§7).
- **Enforcing component:** `constraints.py::validate_required_fields`, invoked
  before every domain check at both gates.
- **Verification method (negative test):**
  `test/offline/test_constraints.py::test_inv_d5_fail_closed` (fixtures
  `d5-missing-required-action`, `d5-null-delta`, `d5-nan-delta`,
  `d5-infinity-price`, `d5-wrong-type-delta`,
  `d5-modeled-unknown-not-block`) removes each required field in turn; supplies
  wrong types, nulls, NaN/Infinity, and unparsable strings expecting `BLOCK`; and
  supplies an explicitly modeled unknown, such as absent portfolio context,
  expecting `REVIEW` rather than `PASS` or a fabricated default.
- **Concrete failure action:** set `BLOCK`; emit `REVIEW`; suppress the
  actionable trade artifact; write `MISSING_FIELD` or `MALFORMED_FIELD` with the
  field path, received type/value, and checkpoint. For a modeled unknown, set
  `REVIEW` with `KNOWN_UNKNOWN` and the field path.

## INV-D6 — Validation after the Trader proposal and again after the final PM output

- **Status:** specified design target — implementation pending gate-1 approval;
  current `constraints.py` is a naive stub (`validate()` always returns `PASS`),
  so this invariant is not yet enforced.
- **Statement:** Every run passes the deterministic guard after the Trader
  proposal and again after the final Portfolio Manager output. The second check
  is not a formality: it may raise a verdict, but it can never lower an earlier
  `BLOCK` or `REVIEW`. A missing gate is a `BLOCK`.
- **Source requirement ID:** `REQ-D-007` (CRS §1; CRS D2 item 3; CRS D3; CRS D4; TP-§7).
- **Enforcing component:** `constraints.py::validate_trader_proposal` and
  `constraints.py::validate_final_decision`, called from `trader.py` and
  `portfolio_manager.py` before their results are returned to the graph.
- **Verification method (negative test):**
  `test/offline/test_constraints.py::test_inv_d6_dual_gate` (fixtures
  `d6-dual-gate-pm-invalid-rating`, `d6-dual-gate-pm-cap-violation`,
  `d6-gate-missing`) covers a Trader proposal that violates the cap or forbidden
  list and stops before risk debate, and a valid Trader proposal followed by an
  invalid PM rating or oversized final decision stopped at the second gate.
  `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_rating_block`,
  `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_cap_block`,
  and `test/offline/test_safety_boundary.py::test_missing_gate_is_block` use
  inline fixtures `VALID_TRADER`, `VALID_PM`, and `KNOWN_BOOK`. These assert both
  gate records exist and the final verdict is the maximum of the two.
- **Concrete failure action:** if either gate is absent, set `BLOCK` with
  `GATE_MISSING`; if either gate fails, preserve its verdict, emit `REVIEW`,
  suppress the actionable trade artifact, and write `DUAL_GATE_FAILURE` with both
  gate records and the merged verdict.

## INV-D7 — BLOCK cannot be overridden by any LLM output

- **Status:** specified design target — implementation pending gate-1 approval;
  current `constraints.py` is a naive stub (`validate()` always returns `PASS`),
  so this invariant is not yet enforced.
- **Statement:** `BLOCK` is final for the run unless an out-of-band signed human
  process supersedes it outside the system. No LLM message, debate argument,
  prompt injection, explanation, regenerated answer, or later check may turn
  `BLOCK` into `REVIEW` or `PASS`. Verdict merging is `max(BLOCK, REVIEW, PASS)`
  and is monotonic. There is no in-system override.
- **Source requirement ID:** `REQ-D-008` (CRS §1; CRS D2 item 3; CRS D3; CRS D4; TP-§7).
- **Enforcing component:** `constraints.py::merge_verdicts` and
  `constraints.py::finalize_verdict`, applied after every gate and after any
  agent-generated text is added to state.
- **Verification method (negative test):**
  `test/offline/test_constraints.py::test_inv_d7_authority` (fixtures
  `d7-block-llm-claim-pass`, `d7-block-regenerated-answer`,
  `d7-lattice-block-over-pass`, `d7-lattice-review-over-pass`,
  `d7-lattice-pass-over-pass`) forces a `BLOCK`, then injects LLM text such as
  "ignore the guard", "override to PASS", or a later valid-looking decision.
  `test/offline/test_constraints.py::test_verdict_domain` uses inline fixtures
  only. `test/offline/test_safety_boundary.py::test_verdict_lattice_is_monotonic`
  uses inline parametrization over `prior` and `expected` verdicts;
  `test/offline/test_safety_boundary.py::test_block_survives_llm_claiming_pass`
  and
  `test/offline/test_safety_boundary.py::test_block_survives_later_valid_looking_decision`
  use inline fixtures `VALID_PM` and `KNOWN_BOOK`. These assert the verdict
  remains `BLOCK`, no actionable trade artifact is emitted, and an override
  attempt is logged, including with the final PM text.
- **Concrete failure action:** retain `BLOCK`; emit non-executable `REVIEW`;
  suppress the actionable trade artifact; write `OVERRIDE_REJECTED` with the
  attempted source, raw text digest, prior and attempted verdicts. Never modify
  the existing verdict record in place.

## INV-D8 — Unknown position is not empty position

- **Status:** specified design target — implementation pending gate-1 approval;
  current `constraints.py` is a naive stub (`validate()` always returns `PASS`),
  so this invariant is not yet enforced.
- **Statement:** An absent portfolio context is `REVIEW`, not a flat book. Only
  an explicit `positions: []` is a flat book. An unknown ticker row, unknown
  quantity, unknown price, unknown cash, or unknown NAV is an explicitly modeled
  unknown and cannot satisfy the position cap; it produces `REVIEW`. Malformed
  portfolio data produces `BLOCK`.
- **Source requirement ID:** `REQ-D-009` (CRS §1; CRS D2 item 3; CRS D3; CRS D4; TP-§7).
- **Enforcing component:** `constraints.py::resolve_position_state` and
  `constraints.py::validate_position_cap`, using the three-state distinction in
  `portfolio.py`.
- **Verification method (negative test):**
  `test/offline/test_constraints.py::test_inv_d8_unknown_position` (fixtures
  `d8-absent-context`, `d8-absent-context-zero-delta`, `d8-explicit-flat`,
  `d8-unknown-nav`, `d8-malformed-portfolio-nav`,
  `d8-malformed-portfolio-positions`, `d8-unknown-ticker-row`,
  `d8-unknown-quantity`, `d8-malformed-position-quantity`) covers absent context
  expecting `REVIEW`; explicit empty positions plus known NAV expecting the cap
  path to run; unknown ticker row, unknown quantity, unknown cash/NAV, and
  currency mismatch expecting `REVIEW`; and malformed portfolio fields expecting
  `BLOCK`.
  `test/offline/test_safety_boundary.py::test_absent_context_is_review_not_flat`,
  `test/offline/test_safety_boundary.py::test_explicit_empty_positions_are_flat`,
  `test/offline/test_safety_boundary.py::test_unknown_nav_is_review_not_zero`,
  and `test/offline/test_safety_boundary.py::test_malformed_portfolio_is_block`
  use inline fixtures `VALID_PM`, `ABSENT`, an explicit empty portfolio with
  known NAV, a portfolio with currency/positions but no NAV, and a malformed
  NAV/positions payload. These assert no case is rendered or treated as zero
  holdings.
- **Concrete failure action:** set `REVIEW`; emit non-executable `REVIEW`;
  suppress the actionable trade artifact; write `POSITION_UNKNOWN` or
  `NAV_UNKNOWN` with the missing input and checkpoint. For malformed data, set
  `BLOCK` with `MALFORMED_PORTFOLIO`; never substitute zero, empty, or `Hold`.

## Gate placement and enforcement notes

- The Trader gate runs after `TraderProposal` is produced and before the risk
  debate reads the proposal.
- The final gate runs after the Portfolio Manager's structured decision (or its
  free-text fallback) and before `final_trade_decision` and `final_rating` are
  returned to the graph.
- The guard validates typed Pydantic objects at the source and revalidates the
  final PM structured decision or rendered text.
- Constraint configuration is validated before any LLM call. Missing or invalid
  configuration fails startup.
- Verdict records are written to the run state and to an append-only JSONL audit
  record.
- The deterministic guard performs no network, LLM, or order I/O.
