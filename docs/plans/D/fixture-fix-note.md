# Fixture Fix Note: d7-lattice-review-over-pass

## Finding (pre-implementation)

Two approved fixtures had byte-identical inputs but contradictory expected
reason codes for a prior `REVIEW` verdict:

- `d4-review-pm-terminal` -> `REVIEW / REVIEW_TERMINAL`
- `d7-lattice-review-over-pass` -> `REVIEW / PRIOR_VERDICT_RETAINED`

Both use:

- stage: `pm`
- proposal: `{"ticker": "AAPL", "rating": "Buy", "delta_quantity": 10, "price": 100}`
- portfolio: `{"nav": 1000000, "currency": "USD", "positions": []}`
- prior_verdict: `"REVIEW"`

A deterministic guard cannot return two different reason codes for identical
inputs, so the suite could not reach 88 passed as written.

## Decision

Option 1, approved by the human owner: align the lattice fixture with INV-D4,
which makes a prior `REVIEW` terminal.

Changed only this field in `test/fixtures/safety_cases.json`:

- Fixture: `d7-lattice-review-over-pass`
- `expected_reason_code`: `PRIOR_VERDICT_RETAINED` -> `REVIEW_TERMINAL`

No verdict, executable flag, input, test, or source change was made.

`PRIOR_VERDICT_RETAINED` remains the expected reason for a prior `BLOCK`
without LLM override text.

## Verification

The stub-only red run is saved as `docs/plans/D/red-run-05.txt`. It remains at
66 failed / 22 passed and does not constitute implementation approval.
