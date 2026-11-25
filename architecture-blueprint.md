# Architecture blueprint

## Role C — Workflow integration

**Contributor:** LiChengzhi (61023334). This section describes delivered behavior and its limits. It does not amend an ADR, grant permission, or certify the entire system.

### Scope and drivers

The workflow produces advisory trading analysis. It preserves the ordinary CLI and Markdown/HTML report paths, configurable legacy research depth, and the Aggressive → Conservative → Neutral risk sequence. The design favors reproducible comparisons, narrow changes to shared state, compatibility with existing checkpoints, and auditable decisions. Optional capture and Guard behavior do not silently replace the default route. There is no broker execution path.

### Components and authority

| Owner | Responsibility and boundary |
| --- | --- |
| A — Evidence | Defines report registration, canonical identity, and immutable snapshot persistence. A valid snapshot reference establishes artifact identity, not the truth or historical availability of its content. |
| B — Research and prompts | Owns research prompts, receipts, and structured review interfaces. A receipt describes what was sent; it is not a checkpoint compatibility guarantee. |
| C — Orchestration | Owns graph routing and state transport, preset selection, ordinary checkpoint lifecycle, budget policy, and the scoped terminal stop marker. Routing does not decide executability. |
| D — Deterministic Guard | Owns the guarded verdict and fallback semantics. Neither model prose nor a later stage may downgrade a stricter verdict. |
| E — Runtime records | Owns CLI activation, reserved run identity, artifact destinations, manifests, reporting, and usage collection. The graph supplies observations; it does not create a second manifest writer. |

### Workflow and observability

1. The graph applies the requested preset to the effective configuration without mutating caller inputs. Omission preserves legacy settings and signatures. Explicit V0 runs two Bull/Bear pairs, explicit V1 runs one, and risk depth is unchanged. Effective depths, recorded settings, and actual prompt receipts are better evidence than a variant label alone. The frozen [`baseline-v0` tag](https://github.com/298994923/TradingAgents-Teamwork/tree/baseline-v0) is a separate regression reference.
2. Selected analysts and the existing Memory Log dependency, when present, join before Bull. Explicit, checkpoint-disabled fresh V0/V1 capture uses that same barrier. It freezes selected report inputs, context, reserved run identity, and one UTC instant. Only successful save or verified identical reuse exposes the five-field reference. A save failure aborts before Bull without publishing a usable reference. Default-off runs bypass capture.
3. Research proceeds through the Research Manager and Trader, then the three risk roles and Portfolio Manager. In opt-in Guard mode the existing deterministic gates govern the result. Only a normal, unguarded V0/V1 final decision receives `stop_reason=completed`; that marker is not a Guard verdict.
4. Ordinary checkpointing uses the same run key for lookup, continuation, and cleanup. A run key distinguishes threads; it does not relax compatibility. An omitted or empty key keeps the legacy thread identity. Successful keyed cleanup preserves sibling and legacy rows. Exact SQLite lookup and cleanup primitives do not constitute locator-based recovery.

### Permissions and change policy

[AGENTS.md](AGENTS.md) and the [permission model](docs/architecture/permission-model.md) describe default-deny, module ownership, and the most restrictive applicable rule. An independent human approves the plan, test version, and scope before feature implementation. Protected-path changes also require a covering ADR and explicit human authorization. Scope, contract, or safety-boundary drift requires re-review; documentation and passing tests do not grant write access. The policy source and effective tool configuration are separate and require separate verification. Publication and approval records remain human-controlled.

### Verification and coverage

Use the [requirements registry](docs/req/requirements.yaml), [invariants](docs/architecture/invariants.md), [structural constraints](docs/code-governance/structural-constraints.md), and [verification constraints](docs/code-governance/verification-constraints.md) to trace fit criteria to tests, including negative controls. Offline verification uses scripted calls, temporary storage, and the existing regression suite. See the [review memo](docs/review-memo.md) for scoped results, not a substitute for whole-system acceptance.

- [ADR-004](docs/architecture/adr/004-budget-and-resume.md) and the [execution-budget contract](docs/contracts/execution-budget.md) separate the standalone budget policy, keyed checkpointing, and the proposed V2 route. V2 runtime, explicit locator recovery, and checkpoint-bound Evidence replay are not covered by this delivery.
- [ADR-005](docs/architecture/adr/005-deterministic-guard.md) and the [Validation-Decision contract](docs/contracts/validation-decision.md) govern Guard authority. [ADR-006](docs/architecture/adr/006-workflow-variant-selector.md) defines preset semantics; [PR #19](https://github.com/298994923/TradingAgents-Teamwork/pull/19) and [PR #21](https://github.com/298994923/TradingAgents-Teamwork/pull/21) distinguish decision adoption from source delivery.
- The [Evidence contract](docs/contracts/evidence.md) and [RunEvent contract](docs/contracts/run-event.md) define the capture and terminal observations. Fresh capture is experimental and default-off; scoped verification does not establish general finalization or crash durability.
- See the [runtime policy catalog](docs/architecture/runtime-policy-catalog.md) and [candidate evaluation table](docs/architecture/evaluation-table.md) for policy triggers and comparison limits.
