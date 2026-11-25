# C-architecture-blueprint-section.md

**Role C discussion draft — input to the team architecture blueprint, not an adopted specification.**

## Scope and ownership

The delivered workflow extends the stock-analysis graph while preserving the default three-role risk path, CLI and HTML reporting, and legacy configuration when no preset is supplied. The `baseline-v0` tag is a historical reference, not the explicit V0 preset. Adaptive V2 and explicit locator-based recovery are outside this delivery.

The graph orchestrates advisory analysis. Evidence registration and persistence, prompt construction and receipts, deterministic Guard decisions, and run reporting retain their separate ownership. A persisted snapshot reference identifies the artifact; it does not certify source quality, historical availability, or a trade recommendation.

## Execution flow

| Boundary | Responsibility | Observable behavior |
|---|---|---|
| Run selection | The CLI forwards the requested preset and run context. The graph resolves the preset without mutating caller configuration. | The effective variant and debate depths are recorded. |
| Analyst fan-in | On the explicitly enabled capture route, all selected analysts and Memory Log join before capture. The default route bypasses capture. | Capture occurs once before Bull; no capture channels appear on the default route. |
| Fresh Evidence | The graph assembles capture inputs; the Evidence API registers and saves the snapshot; the CLI records the resulting reference. | The five-field reference appears only after a successful save. A save failure stops before Bull and leaves the reserved run's failure reference null. |
| Research and risk | Explicit V0 runs two Bull/Bear pairs; explicit V1 runs one. Risk roles remain Aggressive, Conservative, then Neutral. | Route counts, prompt receipts, and report completion can be checked without live model calls. |
| Terminal outcome | The existing Portfolio Manager and Guard paths retain decision authority. | `stop_reason=completed` applies only to normal unguarded final decisions covered by the RunEvent contract. |
| Ordinary checkpointing | Configuration compatibility and run-scoped thread identity remain distinct. | Same-key continuation and exact cleanup preserve neighboring keyed and legacy threads. |

## Public decisions and related drafts

- [ADR-004](../../architecture/adr/004-budget-and-resume.md) defines budget and checkpoint boundaries; [ADR-005](../../architecture/adr/005-deterministic-guard.md) defines Guard authority.
- [ADR-006](../../architecture/adr/006-workflow-variant-selector.md) defines preset behavior. The [RunEvent contract](../../contracts/run-event.md) and [Evidence contract](../../contracts/evidence.md) define terminal and capture observations.
- [C-runtime-policy-catalog.md](C-runtime-policy-catalog.md) describes triggers and failure behavior. [C-candidate-evaluation-table.md](C-candidate-evaluation-table.md) compares the alternatives.
