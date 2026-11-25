# Runtime policy catalog

## Role C — Routing, continuation, and terminal behavior

**Contributor:** LiChengzhi (61023334). This catalog summarizes existing contracts and tested boundaries; it does not introduce a new runtime policy.

| Trigger | Runtime response | Verification boundary |
| --- | --- | --- |
| Selector omitted or `None` | Keep configured research depth and the legacy checkpoint signature. | Legacy controls in [PR #21](https://github.com/298994923/TradingAgents-Teamwork/pull/21). |
| Explicit V0 or V1 | Copy effective configuration, select two or one Bull/Bear pairs respectively, retain risk depth, and include the preset in the compatibility signature. | Route, signature, and real prompt-receipt controls in PR #21. |
| Invalid selector or unavailable V2 | Reject before configuration writes, client construction, or artifact creation. | Negative selector cases in PR #21; no adaptive route delivered. |
| Guard omitted; Guard explicitly enabled | Omission preserves legacy state shape. When enabled, deterministic gates own the verdict and the result records its reason chain. | [PR #12](https://github.com/298994923/TradingAgents-Teamwork/pull/12) and the [Validation-Decision contract](../contracts/validation-decision.md); this is not a general rendering guarantee. |
| Normal, unguarded V0/V1 final decision | Set `stop_reason=completed`. Do not assign this marker for REVIEW, guarded outcomes, or exceptions. | [RunEvent](../contracts/run-event.md) and [PR #37](https://github.com/298994923/TradingAgents-Teamwork/pull/37). An absent marker does not establish success or failure. |
| Ordinary keyed checkpoint continuation | Use the same key for step lookup, continuation, and success cleanup. Disabled mode avoids SQLite. | [PR #18](https://github.com/298994923/TradingAgents-Teamwork/pull/18); not explicit locator recovery. |
| Exact SQLite target absent; deletion fails | Report absence without creating a database. Cleanup targets only the requested rows, rolls back on storage failure, and surfaces the failure. | [PR #17](https://github.com/298994923/TradingAgents-Teamwork/pull/17) covers exact lookup, rollback, and sibling isolation. |
| Capture off; invalid activation | Off keeps the ordinary route; a run ID alone does not enable capture. Explicit malformed context, missing or blank ID, or effective checkpointing is rejected before nodes or Evidence storage access. | [Evidence](../contracts/evidence.md) and [PR #48](https://github.com/298994923/TradingAgents-Teamwork/pull/48). |
| Capture save succeeds or verifies identical reuse | Publish `snapshot_id`, `artifact_key`, `store`, `source_run_id`, and `captured_at` after saving, before Bull. | `REQ-C-CAP-01` in the [registration trace](../req/evidence-registration-trace.md). |
| Capture save fails | Keep the cause, start no Bull or downstream decision, and retain the reserved run ID with a null manifest reference and null sidecar projection in the tested path. | `INV-C-CAP-01` in the registration trace; not a post-manifest failure guarantee. |
| Standalone budget denial or unknown usage | Protect final-review capacity; deny before invocation; distinguish estimates, reported usage (including zero), and unknown usage. | [PR #4](https://github.com/298994923/TradingAgents-Teamwork/pull/4) and [execution-budget](../contracts/execution-budget.md). Policy behavior is not production adaptive routing. |

The [blueprint](../../architecture-blueprint.md) describes ownership. The [evaluation table](evaluation-table.md) separates measured behavior from deferred alternatives.
