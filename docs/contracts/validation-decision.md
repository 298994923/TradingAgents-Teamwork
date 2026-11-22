# Validation-Decision Contract — v1.1

Maintainer: Role D (Liu Kehong, 60894001). Machine-readable contract for the
deterministic guard. Binding version = this file as merged to main at delivery.

## Entry

    validate(proposal, portfolio=ABSENT, stage, prior_verdict=None,
             llm_text=None, config=None) -> GuardResult(verdict, reason_code,
             checkpoint, executable, details)

- Module: src/tradingagents/constraints.py; pure function; structured input only;
  rendered strings are never parsed. ABSENT is distinct from an empty book.
- Guarded mode is opt-in via state["guard_enabled"]; budget enabled with guard
  disabled is refused at startup with CONFIG_INVALID (zero model calls).
- The guard is the single authority for executable=True; no downstream component
  may downgrade or bypass a verdict.

## Semantics

- Lattice merge BLOCK > REVIEW > PASS across checkpoints, monotonic: prior BLOCK
  yields PRIOR_VERDICT_RETAINED; prior REVIEW yields REVIEW_TERMINAL.
- Fail-closed: required field missing or malformed without an upstream record ->
  BLOCK (MISSING_FIELD / MALFORMED_FIELD). A bare ABSENT proposal with no prior
  verdict is such a silent absence -> BLOCK / MALFORMED_FIELD.
- Declared unknown (modeled unknown; upstream stop recorded elsewhere) ->
  non-executable REVIEW (KNOWN_UNKNOWN family). Unknown is never treated as known.
- llm_text is scanned in-memory for execution-leak / override patterns only
  (REVIEW_EXECUTION_LEAK / OVERRIDE_REJECTED); it never upgrades a verdict.
- Hard limits: position cap 10% of NAV post-trade gross, relative tolerance 1e-9;
  forbidden ticker denylist with ALLOWED_EXIT for closing existing positions;
  currency coherence (CURRENCY_MISMATCH); portfolio and nav unknowns
  (POSITION_UNKNOWN / NAV_UNKNOWN / MALFORMED_PORTFOLIO); CONFIG_INVALID at startup.
- Suppression: when executable is false, actionable fields (rating/final_rating,
  action, entry_price, stop_loss, position_sizing, price_target, time_horizon) and
  the FINAL TRANSACTION PROPOSAL line are nulled at every rendering surface.

## Reason codes (20)

PASS, CAP_EXCEEDED, FORBIDDEN_TICKER, ALLOWED_EXIT, INVALID_RATING,
RATING_UNREADABLE, REVIEW_TERMINAL, REVIEW_EXECUTION_LEAK, MISSING_FIELD,
MALFORMED_FIELD, KNOWN_UNKNOWN, GATE_MISSING, DUAL_GATE_FAILURE, OVERRIDE_REJECTED,
PRIOR_VERDICT_RETAINED, POSITION_UNKNOWN, NAV_UNKNOWN, MALFORMED_PORTFOLIO,
CURRENCY_MISMATCH, CONFIG_INVALID

## State key (v1.1)

Guarded runs expose state["guard_result"]:

    {"contract": "validation-decision/1.1", "verdict": "...", "reason_code": "...",
     "checkpoint": "...", "executable": false,
     "rules_hit": [{"checkpoint": "...", "reason_code": "..."}]}

Legacy mode writes no key; absence renders as absent, never PASS.

## Early-stop construction (v1.1)

When a budget stop prevents any guarded node from running, the termination node
constructs the terminal result instead of calling validate: lattice of recorded
verdicts, defaulting to REVIEW / KNOWN_UNKNOWN with checkpoint "budget-stop" and
executable=false; a recorded prior BLOCK is carried as BLOCK / PRIOR_VERDICT_RETAINED.
The budget stop_reason is a separate field and never replaces the verdict. No model
call occurs on this path by construction.

## Revision history

- v1.0 (2026-11-22): issued as appendix to the D to C integration reply; contract
  state key landed as commit 3ae4202.
- v1.1 (2026-11-22): Role C reproduced against candidate 2a5b1f2 that a bare
  validate(ABSENT, prior=None) returns BLOCK / MALFORMED_FIELD. The v1.0 example
  promising REVIEW / KNOWN_UNKNOWN is withdrawn as unimplementable (no input
  channel exists for an upstream stop record). The ABSENT ruling and the
  early-stop construction above replace it. Correction agreed by Role D and
  recorded the same day.
