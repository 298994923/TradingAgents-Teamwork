# C-candidate-evaluation-table.md

**Role C discussion draft — comparison of the delivered presets and the deferred alternative.**

## Alternatives

| Candidate | Mechanism and tradeoff | Disposition |
|---|---|---|
| Frozen `baseline-v0` (`b5d2f67`) | Historical control with configurable debate depth. Useful for software regression; not equivalent to the explicit V0 preset on current main. | Retain as a [tagged baseline](https://github.com/298994923/TradingAgents-Teamwork/tree/baseline-v0). |
| Explicit V0 | Two Bull/Bear pairs, the existing risk path, and the same prompt and reporting interfaces as V1. | Use as the paired control on a common revision. |
| V1 fixed pruning | One Bull/Bear pair removes two research-debate calls relative to explicit V0 without changing risk depth. It also removes one opportunity for either side to respond. | Adopted in [ADR-006](../../architecture/adr/006-workflow-variant-selector.md); [PR #21](https://github.com/298994923/TradingAgents-Teamwork/pull/21) delivered the selector. Prior scripted tests verify route and receipt behavior, not investment quality. |
| V2 adaptive collaboration | Proposed unresolved-question and budget-aware routing with eligibility, bounded rounds and final-review reservation. Introduces additional state and integration requirements. | The research-budget design is documented in [PR #23](https://github.com/298994923/TradingAgents-Teamwork/pull/23). No delivered V2 graph acceptance is claimed. |

## Comparison method

For a measured comparison, hold the revision, ticker, date, analyst selection, model configuration and sampling settings fixed. Compare explicit V0 and V1 on research calls and reported input/output tokens. Isolate prompt compression in a separate comparison at the same policy variant. Keep failures in the denominator and label missing usage as unknown. Report decision-quality outcomes only against a defined evaluation method.

See [C-architecture-blueprint-section.md](C-architecture-blueprint-section.md) for the delivered boundaries and [C-verification-and-closeout-evidence.md](C-verification-and-closeout-evidence.md) for prior offline results.
