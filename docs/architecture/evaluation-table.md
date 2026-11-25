# Candidate evaluation table

## Role C — Fixed and adaptive workflow alternatives

**Contributor:** LiChengzhi (61023334).

| Candidate | Benefit | Cost or limitation | Disposition and evidence |
| --- | --- | --- | --- |
| Frozen `baseline-v0` | Reproducible historical reference for software regression. | Different revision; not equivalent to the explicit V0 preset or selector omission on main. | Retain the [frozen tag](https://github.com/298994923/TradingAgents-Teamwork/tree/baseline-v0). |
| Explicit V0 | Two Bull/Bear pairs provide the paired control for V1 under the same interfaces. | One additional exchange relative to V1; no demonstrated improvement in decision quality. | Delivered control in [PR #21](https://github.com/298994923/TradingAgents-Teamwork/pull/21). |
| V1 fixed pruning | One Bull/Bear pair removes two research-debate calls relative to explicit V0 while preserving risk depth. | Gives each side one fewer opportunity to respond; call savings are not measured token savings. | [ADR-006](adr/006-workflow-variant-selector.md) and PR #21; scoped offline route and receipt checks, not investment-quality evidence. |
| V2 adaptive collaboration | Could spend a bounded budget on eligible responses to unresolved questions and protect final-review capacity. | Requires progress and eligibility signals, per-invocation settlement, bounded routing, and integrated stop acceptance. | Research-budget design documented in [PR #23](https://github.com/298994923/TradingAgents-Teamwork/pull/23); no delivered V2 runtime result claimed. |

### Measurement protocol

Pair explicit V0 and V1 on the same revision, ticker, analysis date, analyst selection, model configuration, sampling settings, and input conditions. Compare completed research calls, reported input/output tokens, run failures and terminal outcomes. Keep failed attempts in the denominator and label missing usage unknown. Hold policy variant fixed for any separate prompt-compression comparison. Report decision quality only against a defined evaluation method. The prior scripted suite shows the route and receipt behavior; no new benchmark or live-model comparison was run for this table.
