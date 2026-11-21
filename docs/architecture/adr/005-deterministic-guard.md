# ADR-005: Deterministic Guard Authority

- **Status:** Proposed; the safety-guard module maintainer adopted the
  recommended parameter options on 2026-11-21. Human reviewer sign-off is
  pending.
- **Date:** 2026-11-21
- **Decision owner:** safety-guard module maintainer
- **Reviewer:** human reviewer
- **Supersedes:** none
- **Related:** `docs/architecture/invariants.md`,
  `docs/plans/D/requirements-pack.yaml`, `.opencode/rules.md`

## Context

The trading pipeline is a multi-agent LLM system. Analysts, researchers, risk
debaters, the Trader, and the Portfolio Manager produce natural-language
reasoning and structured proposals. Their output is useful but nondeterministic,
prompt-injectable, and not a reliable place to enforce hard safety limits.

The current code has useful schemas and explicit `REVIEW` handling, but no
deterministic component that owns the final safety verdict. The project rules
require deterministic verdicts to be final, unknown positions not to be treated
as empty, insufficient information to produce `REVIEW`, missing or malformed
fields to fail closed, and no LLM output to turn `BLOCK` into `PASS`.

This ADR records the authority model and the adopted parameter values for the
safety guard. The guard will be implemented in `constraints.py` and invoked from
safety-guard-owned decision code.

## Decision

The AI agents are advisory. Deterministic code in `constraints.py` is
authoritative.

The guard returns one of `PASS`, `REVIEW`, or `BLOCK`. The verdict lattice is:

`BLOCK > REVIEW > PASS`

Merging takes the maximum severity. Once raised, a verdict is monotonic and is
never lowered by a later check, agent message, debate argument, regenerated
answer, or prompt injection.

`REVIEW` is terminal and non-executable: no retry, no order, no actionable trade
artifact. `BLOCK` is also non-executable and has no in-system override.
Exceptions require an out-of-band signed human process and a new or amended ADR;
no LLM can issue one.

The guard is invoked twice: after the Trader proposal and again after the final
Portfolio Manager output. It validates typed objects at the source and
revalidates the final PM structured decision or rendered text. A missing gate is
a `BLOCK`.

### Adopted policy values

- Position cap: **10% of NAV**, measured as **gross absolute post-trade
  exposure** (`abs(current quantity + proposed delta) * price`). Equality is
  allowed: `exposure <= cap`.
- Numeric comparison: with `cap = 10% of NAV` and `exposure = gross absolute
  post-trade exposure`, all arithmetic uses `Decimal`. Within-cap iff
  `exposure <= cap + cap * Decimal("1e-9")`; over-cap (`BLOCK` /
  `CAP_EXCEEDED`) iff `exposure > cap + cap * Decimal("1e-9")`. Equality is
  allowed, and no larger policy buffer is permitted.
- Forbidden list: static, human-curated file. It is seeded with the single
  illustrative entry `DEMO-BAN`, clearly marked as an example for tests and
  demos. Real entries are added only by a human.
- Forbidden action scope: block exposure-increasing actions only; reductions and
  exits are allowed. Matching uses the existing normalized ticker form.
- Ratings: `Buy`, `Overweight`, `Hold`, `Underweight`, `Sell` for the Research
  Manager and Portfolio Manager; the Trader action remains `Buy`/`Hold`/`Sell`.
  Matching is case-insensitive trimming to canonical values; no aliases.
- Fail-closed: missing or malformed required fields, schema failures, and parse
  failures produce `BLOCK`. Explicitly modeled unknowns produce `REVIEW`.
  Unknown position is never treated as flat.
- Portfolio states: absent context is `REVIEW`; explicit empty positions are
  flat; malformed data is `BLOCK`; unknown NAV/cash needed for the cap is
  `REVIEW`; currency mismatch is `REVIEW`.
- Verdict authority: maximum-severity, monotonic merge; no in-system override.
- Execution path: any actionable trade artifact, including a Buy/Sell
  instruction with non-zero sizing or quantity, and any future order-dispatch
  call. Reports, state logs, and audit records are not execution artifacts.
- Audit: a verdict record in final state plus an append-only JSONL record per
  run.
- Verification: every new test lives under `test/offline/`, in
  `test/offline/test_constraints.py` and
  `test/offline/test_safety_boundary.py`.

### Source anchors

- **CRS §1 (Project Overview):** safety boundary / deterministic constraint.
- **CRS D2 item 3:** invariant register five elements.
- **CRS D2 item 6:** permission model default-deny whitelist.
- **CRS D3:** negative test per feature and safety-critical ADR plus human
  approval.
- **CRS D4:** every invariant has at least one negative test that fails on
  violation.
- **TP-§7:** team plan D tasks.

### Parameter decisions and one-line rationales

| TBD | Adopted decision | Rationale |
|---|---|---|
| TBD-D-01 | Percent of portfolio NAV per instrument | NAV normalization makes the cap comparable across instruments and account sizes; the guard already needs NAV to fail closed. |
| TBD-D-02 | 10% of NAV | A 10% default constrains concentration while leaving valid ideas usable; the value stays configurable. |
| TBD-D-03 | Per-instrument gross absolute post-trade exposure | Gross absolute exposure is the conservative measure and cannot be hidden by netting. |
| TBD-D-04 | Post-trade position (holding + delta) | Checking the result, not just the delta, prevents an already-oversized holding from passing on a small trade. |
| TBD-D-05 | Equality allowed (`exposure <= cap`) | An inclusive boundary is deterministic and testable; precision is handled separately. |
| TBD-D-06 | Decimal arithmetic: within-cap iff `exposure <= cap + cap * Decimal("1e-9")`; over-cap iff `exposure > cap + cap * Decimal("1e-9")` | The explicit tolerance absorbs Decimal/floating-point noise without creating a larger policy buffer. |
| TBD-D-07 | Static human-curated file seeded with illustrative `DEMO-BAN` | A static list is auditable and deterministic; `DEMO-BAN` exercises blocking in tests and demos without pretending to be live policy. |
| TBD-D-08 | Block exposure-increasing actions only; allow reductions and exits | This stops harm while still allowing a forbidden position to be reduced or exited. |
| TBD-D-09 | Normalized ticker exact match | The existing normalizer is deterministic and handles broker spellings; issuer-level aliases are deferred. |
| TBD-D-10 | PM final rating and Research Manager recommendation as 5-tier; Trader action as 3-tier | This covers both 5-tier decision artifacts while validating the Trader against its own schema. |
| TBD-D-11 | Case-insensitive trim to canonical values; no aliases | Harmless formatting variation is accepted without allowing aliases that change meaning. |
| TBD-D-12 | Terminal `REVIEW`, no retry | A terminal no-retry disposition is deterministic and keeps `REVIEW` out of the execution path. |
| TBD-D-13 | Missing/malformed required fields -> `BLOCK`; modeled unknown -> `REVIEW` | This enforces fail-closed for bad data while preserving a distinct, non-tradeable unknown state. |
| TBD-D-14 | Absent context -> `REVIEW`; explicit empty -> flat; malformed -> `BLOCK`; unknown NAV/cash -> `REVIEW` | This preserves the three portfolio states and prevents unknown inputs from silently becoming zero. |
| TBD-D-15 | `BLOCK > REVIEW > PASS`, maximum severity, monotonic | Maximum-severity monotonic merging ensures no later result or LLM output can erase a `BLOCK`. |
| TBD-D-16 | No in-system override; out-of-band signed human process and new ADR only | Removing in-system override preserves the invariant while leaving a controlled human exception path. |
| TBD-D-17 | Fail startup before any LLM call | No decision should run under an unvalidated guard configuration. |
| TBD-D-18 | Any actionable trade artifact or future order dispatch | This covers today's advisory output and future execution without forbidding audit records. |
| TBD-D-19 | Validate typed objects at source and revalidate the final PM output | Two checks catch both schema errors and rendering or tampering drift. |
| TBD-D-20 | Require matching currencies; mismatch -> `REVIEW` | This avoids unsafe raw-number comparisons and avoids a nondeterministic FX dependency. |
| TBD-D-21 | Final-state verdict plus append-only JSONL per run | This provides auditable, queryable evidence while keeping the guard local and deterministic. |
| TBD-D-22 | One negative test per invariant and 100-run determinism checks | Behavior-focused thresholds verify the guarantees rather than relying on line coverage. |
| TBD-D-23 | Source anchors: CRS §1; CRS D2 items 3 and 6; CRS D3; CRS D4; TP-§7 | These real course and team-plan clauses replace the former source-label placeholders; no deferred source anchor remains. |

All TBD-D parameter and source decisions are resolved; no documentation
placeholder remains.

## Alternatives considered

### 1. LLM-only risk debate

Let the risk analysts and Portfolio Manager enforce safety through prompt
instructions and debate.

- Advantages: no new deterministic component, no configuration surface, no extra
  code path.
- Disadvantages: nondeterministic verdicts, prompt-injection exposure, no
  reproducible audit trail, no machine-checkable guarantee, and no defensible
  answer to "why was this BLOCK not enforced?"
- Rejected because it cannot satisfy rule 10 or the hard invariants.

### 2. Hybrid with an LLM judge or LLM veto

Run deterministic checks but let an LLM judge override, soften, or veto their
result.

- Advantages: potentially more nuanced treatment of edge cases and fewer false
  blocks.
- Disadvantages: the LLM becomes the final authority, verdicts vary across runs
  and providers, and a prompt injection can turn `BLOCK` into `PASS`.
- Rejected because it breaks the required authority model. An LLM may explain a
  verdict, but it cannot change one.

### 3. Deterministic guard authoritative, LLM advisory (chosen)

The agents propose and explain. The deterministic guard decides whether the
proposal is `PASS`, `REVIEW`, or `BLOCK`.

- Advantages: reproducible verdicts, negative-testable behavior, auditable
  reason codes, fail-closed handling, and a clear authority boundary.
- Disadvantages: configuration and data completeness become prerequisites;
  legitimate but underspecified ideas may become `REVIEW`.
- Chosen because it is the only option that makes the invariants enforceable.

## Consequences

Positive:

- Safety limits are enforced by code rather than by prompt compliance.
- Verdicts are deterministic, monotonic, and auditable.
- Each invariant has a clear negative test under `test/offline/`.
- Unknown positions and malformed fields cannot silently become tradeable.
- The project can demonstrate a defensible answer to LLM override attempts.

Negative:

- A 10% cap and strict fail-closed behavior will increase `REVIEW` and `BLOCK`
  counts compared with prompt-only guidance.
- Complete NAV, position, price, and currency data are required for a cap check to
  pass.
- The forbidden list is empty apart from the illustrative `DEMO-BAN` entry until
  humans populate it.
- Cross-currency portfolios are not supported; they produce `REVIEW`.
- Configuration errors fail the run at startup, which can block demos if the
  guard configuration is incomplete.

Neutral:

- A new state or audit field may be needed. The coding agent must not edit the
  protected integration files or `agents/schemas.py` without an ADR plus
  explicit human approval; integration points are coordinated under human
  review.
- No broker execution path exists today. The execution-path definition is written
  now so future order dispatch cannot bypass the guard.

## Risks and mitigations

- **False blocks from incomplete data:** use explicit `REVIEW` for modeled
  unknowns and require the caller to supply complete portfolio context for a
  tradeable result.
- **Forbidden list mistaken for live policy:** keep `DEMO-BAN` clearly marked as
  an example and require human curation for real entries.
- **Configuration typo disabling protection:** validate configuration at startup
  and fail before any LLM call.
- **Later agent masking an earlier block:** use maximum-severity monotonic
  merging and never rewrite an existing verdict record.
- **Review text leaking into an execution artifact:** define execution as any
  actionable trade artifact and assert in tests that `REVIEW` produces none.
- **Non-deterministic FX conversion:** reject currency mismatches with `REVIEW`
  rather than adding a live FX dependency.

## Reopen conditions

This ADR must be revisited if any of the following occurs:

- The position cap value or NAV basis changes.
- The forbidden list needs an external or dynamic source.
- Broker or order execution is added.
- A new asset class needs a different exposure or NAV model.
- Cross-currency portfolios must be supported.
- Observed false-block or false-review rates exceed a human-approved threshold.
- The rating vocabulary changes.
- A human override process is adopted.
- Provider structured-output behavior makes the current validation representation
  insufficient.
- The course requirement sheet or team plan adds a conflicting requirement.

## Traceability

- Invariants: `docs/architecture/invariants.md` (INV-D1 through INV-D8).
- Requirements: `docs/plans/D/requirements-pack.yaml` (REQ-D-001 through
  REQ-D-013).
- Human-only rules: `.opencode/rules.md` rules 4, 5, 8, 9, and 10.
- Source anchors: CRS §1; CRS D2 items 3 and 6; CRS D3; CRS D4; TP-§7.
- Planned verification: `test/offline/test_constraints.py` and
  `test/offline/test_safety_boundary.py`.
