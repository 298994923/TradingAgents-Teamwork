# C-runtime-policy-catalog.md

**Role C discussion draft — inventory of delivered runtime behavior, not an adopted policy.**

## Routing and failure policies

| Trigger | Runtime response | Verification boundary |
|---|---|---|
| Selector omitted or `None` | Keep legacy configuration and checkpoint signature. | Fixed-pruning legacy controls. |
| Explicit V0 or V1 | Copy the effective configuration, set two or one Bull/Bear pairs respectively, and preserve risk depth. Include the preset in the compatibility signature. | Fixed-pruning and prompt-receipt controls. |
| Invalid variant or unavailable V2 | Reject before graph construction side effects. | Selector negative controls; no adaptive route is delivered. |
| Guard omitted or enabled | Omission retains the legacy route. When enabled, the deterministic verdict remains authoritative and its result retains the reason chain. | Legacy and opt-in Guard controls; report rendering is a separate boundary. |
| Normal unguarded final decision | Record `stop_reason=completed`. | The terminal policy does not assign `completed` to REVIEW, guarded outcomes, or exceptions. |
| Compatible ordinary keyed continuation | Use the same run-scoped thread for lookup, execution and cleanup. | Verify the target and preserve neighboring keyed and unkeyed threads. |
| Exact lookup or cleanup finds no target | Report absence without creating a database. Exact cleanup deletes only target rows in a transaction and surfaces storage errors. | SQLite absence, isolation and rollback controls; not locator-based recovery. |
| Evidence capture disabled | Keep the ordinary route. A run ID alone does not activate capture. | Default-off and graph reuse controls. |
| Malformed capture context, missing or blank ID, or effective checkpointing | Reject before running nodes or accessing Evidence storage. | Activation and checkpoint refusal controls. |
| Capture save reports `created` or `already_present` | Publish the reference with snapshot ID, artifact key, store, source run ID and capture time, then allow Bull to proceed. | `REQ-C-CAP-01`: V0 and V1 capture positives. |
| Capture save raises | Preserve the Evidence error and cause, start no Bull or downstream decision, and retain the reserved run ID with a null reference in the failure manifest and sidecar. | `INV-C-CAP-01`: failed-save CLI case; not a general reporting-failure claim. |
| Standalone budget admission denies work or usage is unknown | Protect final-review capacity and keep unknown usage distinct from reported usage. | Standalone policy controls only; V0/V1 do not perform adaptive budget routing. |

## Scope limits

Fresh capture is experimental, explicit, and default-off. The [Evidence contract](../../contracts/evidence.md), [RunEvent contract](../../contracts/run-event.md), and [execution-budget contract](../../contracts/execution-budget.md) define the relevant interfaces. See [C-verification-and-closeout-evidence.md](C-verification-and-closeout-evidence.md) for prior test evidence and its limits.
