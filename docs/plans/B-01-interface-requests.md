# Package B interface requests

Proposals for review. Delivery and acceptance by the named teams remain pending. C owns state and graph changes. Defaults apply only to new collaboration sessions; missing fields in legacy state must preserve legacy behavior.

| Requested from C | Purpose | Writer | Reader | Default | Missing or incompatible during collaboration |
|---|---|---|---|---|---|
| claims | Stable ledger for references and blind prompt assembly | C merges validated researcher deltas | B researchers and manager | Empty list | Reject a later-round reference without a ledger |
| round_index | Distinguish blind and targeted phases | C scheduler | B context builder | 1 for a new run | Reject ambiguous resumed phase |
| responded_claim_ids | Track completed targets, distinct from assigned targets | C records accepted B responses | C scheduler and B manager | Empty list | Reconstruct only from validated links; otherwise mark unresolved |
| unresolved_questions | Carry disagreements through fallback and resume | B proposes changes; C persists them | B manager and D | Empty list for a new run | Preserve the last validated list and signal degradation |
| context_meta | Attach schema version, budgets, layer estimates and dropped IDs/reasons | B emits; C persists | C and E | Empty mapping for legacy | Mark estimates unavailable; reject incompatible resume |
| target_claim_ids | Tell each researcher which earlier claims are assigned | C scheduler | B researcher | Empty list | Emit no-target reason; never choose a substitute autonomously |

**A — evidence validation.** Proposed callable: check(evidence_id, as_of) returning a verdict with status (valid, malformed, missing, future, unknown_time), canonical ID, timestamp when known and reason. Please confirm types, timezone, cutoff inclusivity and behavior on service failure. Strict historical review rejects unverifiable citations. Offline fixtures can inject the checker until integration.

**D — field intake.** Please supply each hard constraint's stable ID, exact text, scope, source and version, together with required manager and degradation fields. Identify a consumer and a negative fixture per proposed field. B records accept, reject with reason, or defer with debt at S8. D retains final enforcement.

**E and metric author NanLi — metric contract.** Please confirm schema ownership, provider coverage, node timing and publication of sanitized results under the ignored results directory. B needs run-level prompt/completion counts, stage elapsed time, model name and prompt hash. Use totals.tokens_in/out, timing.by_node_sec and run_settings only at their recorded granularity. An inclusive node duration may cover multiple rounds. Proposed B sidecar links the manifest run_id, prompt version/hash, case ID, invocation coverage and layer estimates. Keep missing actuals null with a reason. Archive each comparison manifest before another run overwrites the ticker/date path. B requests no edits to the shared writer.
