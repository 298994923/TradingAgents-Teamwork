# 006-workflow-variant-selector.md

**ADR-006 | Main candidate | English revision for D review | Pending adoption; this document does not authorize source changes**

Historical review baseline: `main@ab30058506b62fc14d403395b7cbb36122c0d343`. This candidate follows C-v1-workflow-variant-adr-addendum.md (v0.1). D-to-C-integration-governance-replies.md approved the original decision text and assigned ADR-006; the main candidate changed only the delivery target and acceptance boundaries. `ADR-001` in C-v1-fixed-pruning-plan-v0.2.md is a historical draft reference and remains unchanged. At that baseline, the only ADR present was `005-deterministic-guard.md`; this ADR had not been adopted.

## Decision

The fixed-pruning experiment compares two Bull/Bear pairs with one on the same commit, with all other settings held constant. It does not change global defaults. `TradingAgentsGraph` adds the keyword-only parameter `workflow_variant: str | None = None`. The base configuration is still selected with `config or DEFAULT_CONFIG`: a nonempty caller configuration takes precedence; an omitted or empty configuration uses `DEFAULT_CONFIG`. No configuration merge is added.

| Selector | Effective research debate depth | Configuration and behavior |
| --- | --- | --- |
| Omitted or `None` | Use the configured depth; the built-in default is one pair | Preserve the legacy path, run-settings keys, and checkpoint signature. |
| `workflow_variant="v0"` | Two rounds, one Bull/Bear pair per round | Shallow-copy the base configuration and override only `max_debate_rounds`. |
| `workflow_variant="v1"` | One round, one Bull/Bear pair | Shallow-copy the base configuration and override only `max_debate_rounds`. |

An explicit preset overrides the configured research depth without modifying the caller's configuration, `DEFAULT_CONFIG`, or `max_risk_discuss_rounds`. Existing routing, the Aggressive → Conservative → Neutral risk sequence, and the Portfolio Manager remain unchanged. Reject `"v2"` with `ValueError` because it is not available. Reject other invalid values, including `"v3"`, `"V1"`, the empty string, and integers, with `ValueError` for an invalid selector. Validate before calling the global `set_config`, creating directories or artifacts, constructing clients, or calling models.

- `run_settings()` exposes the effective `max_debate_rounds` and `max_risk_discuss_rounds`. Only explicit presets add `workflow_variant`. The existing `full_states_log_<trade_date>.json` stores the same values under `run_settings`. Existing report entry points are unchanged.
- `_run_signature()` uses the effective configuration. Omission or `None` preserves the original signature. Explicit presets append `workflow_variant=v0` or `workflow_variant=v1`, distinguishing an explicit preset from a legacy call even for the same ticker, date, and depth. Explicit signatures are stable for identical effective inputs. SQLite storage and resume behavior are unchanged.
- **Experimental control.** Explicit `v0` is the two-round control for explicit `v1` on the same commit. `baseline-v0` is the frozen Git tag used for regression (pointing to `b5d2f6714e98724506262cca7d38d62f4613d91b`); it is neither this preset nor an alias for omitting the selector.

This decision covers only the programmatic selector and its offline verification. It does not change the CLI, manifest, Guard, V2 routing, checkpoint storage, or report writers. A CLI label is not evidence of the depth actually executed.

## Historical evidence and review-baseline verification

1. **Red tests first.** The appendix in C-v1-fixed-pruning-delivery-review.md records an independent run on `f4957b20fadef9809bc314be0be1a8fc0782ad08`: 2 passed and 9 failed. All nine failures were due to the constructor not accepting `workflow_variant`.
2. **Local prototype and reruns.** The focused suite passed all 11 cases. The offline regression had 1,513 passes, 1 skip (missing `langchain_aws`), 1 deselection, and 100 passing subtests. `git diff --check` passed. Later, the operands of one equality assertion were swapped solely for Ruff; the assertion's behavior was unchanged. Ruff and all 11 focused tests passed on rerun.
3. **Independent technical review followed the prototype.** In D-to-C-alignment-and-v1-review.md (2026-11-22, Part B), D gave the existing prototype a technical `APPROVE` and delivery `APPROVE WITH EVIDENCE`. D did not run the candidate. This review was not pre-implementation approval for the prototype and does not replace the formal delivery record.
4. **Integration reproduction.** C-v1-integration-verification.md records 11 focused passes for the original candidate on `integration@0531db16a75f936c836255a5ce44986119334701`. The offline regression had 1,713 passes, 1 skip (missing `langchain_aws`), 1 deselection, 100 passing subtests, and 24 warnings. Ruff passed for the candidate files; the 69 existing repository-wide diagnostics were unchanged. The later receipt review used a different integration baseline and an adapted patch; it was not acceptance on `main`.
5. **Original main review check.** At the historical main review baseline above, the original source patch from the appendix passed `git apply --check --index --whitespace=error-all`. It was not applied. The target `trading_graph.py` already contained a separate Guard change outside the source patch's scope. The reviewed source hash identifies the historical candidate, not the file produced by applying the patch to that target. No tests were run during that check.

| Pinned material | SHA-256 |
| --- | --- |
| Original source patch in the appendix of C-v1-fixed-pruning-delivery-review.md | `951aa235a7d655595a515da0c26fc23b880f588a4b2f191fa9237bf5529979e9` |
| Originally reviewed `trading_graph.py` (historical candidate) | `fefce348c01c29f72e70b0be4e6645e8e9e77496148b718e36f40c76b43a0274` |
| `test_v1_fixed_pruning.py` (11 cases) | `6b8b412a29f7af2fc03f1b5b531b75171b39c97b03e29c0acec2fe723b4e5099` |
| `test_v1_prompt_receipts.py` (3 cases) | `072581696ab832d2ace3825481fd69e83870a4e35b02734e763a2412f00e6126` |

## Staged acceptance

- **Interim acceptance — V1 not complete.** The original 11 cases do not depend on B. After authorization, reproduce the red run against the actual delivery baseline first. Then run the original 11 cases, existing legacy checkpoint regressions, the full offline suite, Ruff, and `git diff --check` on the same candidate. The focused suite covers omission and `None`, explicit two- and one-pair debates, the three-role risk flow, reports and the state log, signatures, and rejection before side effects.
- **Final acceptance — 14 cases on one candidate.** At the historical main review baseline there was no `on_prompt` constructor argument or forwarding to `GraphSetup`. The pinned `test_v1_prompt_receipts.py` cases for omission, `v0`, and `v1` all require B's real wiring. Once it reaches `main`, run both pinned V1 test files and the existing receipt controls on the same candidate, verifying ordered role receipts and digests against the actual model inputs. No replacements, skipped cases counted as passes, or shims. The 14-case same-candidate gate from D's integration ruling remains in force. Eleven passes are interim only.

## Adoption and protected source

This revision is documentation only: it does not adopt ADR-006 or implement the selector. The original candidate called for team visibility and adoption through a standalone documentation PR merged to `main`, followed by separate confirmation of the protected source scope and staged acceptance. D-to-C-v1-main-delivery-ruling.md records the subsequent decision, signed by Liu Kehong (Role D, `60894001`) on 2026-11-23: D approved the pinned original document for the standalone PR, conditionally authorized the pinned source patch and 11-case test on actual `main` **after** ADR adoption, and approved interim acceptance without waiving the final gate. This ruling is separate from D's integration-specific authorization and does not sign off on these new English bytes.

The conditional source scope covers only `src/tradingagents/graph/trading_graph.py` with the pinned selector test and the verification above. If the delivery baseline moves, rerun the apply check and record any context-only shifts in the source PR. Return to D before applying if there is a substantive difference in the constructor, validation, `_run_signature()`, or `run_settings()`; any overlap with Guard, opt-in, or transport-channel lines; or a test hash change. A post-B wiring conflict also goes back to D for review of the adaptation. Humans maintain the formal records with actual dates, scope, and sequence; the source PR ledger must cite `60894001` and D-to-C-v1-main-delivery-ruling.md. ADR adoption does not waive the other delivery conditions.
