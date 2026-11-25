# Trace Matrix

Owner: A (aggregated from all members' requirement packs). Status: derived from
`docs/req/requirements.yaml` (58 entries). For each requirement: enforcing
component, test/evidence, and runtime monitor. `—` means no runtime monitor is
defined for that requirement. A selector marked `pending-*` is a planned test
registered in the requirements registry, **not** proof of a pass.

## Role C — workflow, budget, resume, checkpoints, capture

| REQ | Enforcing component | Test / evidence | Runtime monitor |
|---|---|---|---|
| REQ-C-01 | `src/tradingagents/execution_policy.py` | `test/offline/test_execution_policy.py::test_same_input_scales_with_budget`; pending whole-graph C-P01 | `stop_reason` in manifest |
| REQ-C-02 | `execution_policy.py` | `test_execution_policy.py::test_denied_call_preserves_reservation_and_is_not_invoked`, `::test_t_p1_failed_reservation_locks_the_terminal_state`; pending C-P02 | guard envelope / non-executable outcome |
| REQ-C-03 | `execution_policy.py` + `src/cli/stats_handler.py` | `test_execution_policy.py::test_reservation_is_reported_separately_from_usage`, `::test_missing_usage_is_unknown_not_zero`; pending C-P03 | `usage` + per-call settlement |
| REQ-C-04 | graph scheduling (C) | pending C-P04 whole-graph eligibility/progress/cap | `research_stop_reason` |
| REQ-C-05 | `src/tradingagents/graph/{checkpointer,trading_graph}.py` | `tests/test_graph_end_to_end.py::test_an_interrupted_run_resumes_from_its_checkpoint`; `test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`; pending C-P05 | checkpoint locator / run key |
| REQ-C-06 | graph setup + ADR-006 selector | `tests/test_graph_end_to_end.py::test_a_full_run_reaches_a_logged_decision`; `test_v1_fixed_pruning.py::test_omitted_variant_keeps_default_route` etc. | `config_snapshot.workflow_variant` |
| REQ-C-FR-01, INV-C-FR-01, INV-C-FR-02, INV-C-FR-03 | `graph/trading_graph.py` (keyword-only variant) | `test/offline/test_v1_fixed_pruning.py` (explicit v0/v1 depth, rejected v2, legacy signature) | `run_settings().workflow_variant` |
| REQ-C-CKPT-01 / INV-C-CKPT-01 | `graph/checkpointer.py`, `graph/trading_graph.py` | `test/offline/test_checkpoint_graph_run_key.py`, `test_checkpoint_graph_prompt_receipts.py` | exact thread key in SQLite |
| REQ-C-STOR-01, REQ-C-STOR-02, REQ-C-STOR-03, REQ-C-STOR-04, INV-C-STOR-01, INV-C-STOR-02, INV-C-STOR-03, INV-C-STOR-04 | `graph/checkpointer.py` | `test/offline/test_checkpoint_thread_identity.py`, `test_checkpoint_run_key_storage.py`, `test_checkpoint_exact_thread_lookup.py`, `test_checkpoint_exact_thread_cleanup.py` | checkpoint lookup/cleanup logs |
| REQ-C-CKPT-02 / INV-C-CKPT-02 | checkpoint preflight (C) | pending `test_explicit_checkpoint_preflight_main.py` (6 cases) | preflight rejection diagnostics |
| REQ-C-CAP-01 / INV-C-CAP-01 | C capture node + A's `evidence.save_snapshot` | `test/offline/fresh_evidence_capture/test_fresh_evidence_cli_review.py` (v0/v1, save-failure abort) | `evidence_snapshot` in state + manifest |

## Role A — evidence

| REQ | Enforcing component | Test / evidence | Runtime monitor |
|---|---|---|---|
| A-EV-08 | `src/tradingagents/evidence.py` (`artifact_key_for` / `parse_artifact_key`) | `test/offline/test_evidence_artifact_keys.py` (6 cases) | artifact key ↔ snapshot ID round trip |

> **Gap:** A's remaining evidence requirements (registration, time validity, snapshot save/load) are not yet registered in `requirements.yaml`; their tests live in `test/offline/test_evidence.py` and `test/fixtures/evidence_cases.json`. A to add REQ-EV entries.

## Role B — review, context, prompts

| REQ | Enforcing component | Test / evidence | Runtime monitor |
|---|---|---|---|
| B-REQ-01, B-REQ-02, B-REQ-03, B-REQ-04, B-REQ-05, B-REQ-09, B-REQ-10 | `src/tradingagents/review.py`, `agents/researchers/*`, `agents/managers/research_manager.py` | `test/offline/test_review.py` **missing in this checkout** (claims in registry); `test_context_builder.py::test_blind_round_and_reverse_control`, `test_fingerprint`, `test_claim_validation`, `test_repair_once`, `test_manager_decision` | prompt receipts (`b.<role>` hashes) |
| B-REQ-06, B-REQ-07, B-REQ-08, B-REQ-12 | `src/tradingagents/context_builder.py` | `test/offline/test_context_builder.py::test_budget_boundary_and_compaction`, `::test_impossible_budget`, `::test_context_dedup`, `::test_metrics_and_placement` | context budget metrics |
| B-REQ-11 | evaluation protocol + `scripts/compare_runs.py` | `test/live/test_baseline_compare.py::test_matched_protocol` (live, requires keys) | `docs/evaluation/results/` |

> **Gap:** `test/offline/test_review.py` is referenced by 6 B requirements but does not exist. B to restore or re-point the selectors.

## Role D — deterministic safety

| REQ | Enforcing component | Test / evidence | Runtime monitor |
|---|---|---|---|
| REQ-D-007 | `src/tradingagents/constraints.py` (dual gate, verdict lattice) | `test/offline/test_constraints.py::test_inv_d6_dual_gate`; `test/offline/test_safety_boundary.py` (6 cases) | `guard_result` in final state / report masking |

> **Gap:** D's invariant register (`docs/architecture/invariants.md`, INV-D1…8) and REQ-D-001…006/008…013 are not in `requirements.yaml`; see `docs/plans/D/requirements-pack.yaml` (draft). D to register.

## Role E — runtime records, metrics, governance

| REQ | Enforcing component | Test / evidence | Runtime monitor |
|---|---|---|---|
| REQ-E-01 | `src/tradingagents/run_recorder.py` | `test/offline/test_run_recorder.py`; `docs/contracts/run-event.md` | manifest v1 (15 fields) |
| REQ-E-02 | `src/cli/stats_handler.py` | `test/offline/test_usage_window.py`, `test_stats_calls.py` | per-call usage / tokens |
| REQ-E-03 | `scripts/compare_runs.py` | `test/offline/test_compare_runs.py`; `docs/evaluation/protocol.md` | guard-key equality check |
| REQ-E-04 | `scripts/compare_runs.py` + results docs | `docs/evaluation/results/` | published comparison tables |
| REQ-E-05 | `src/tradingagents/{reporting,report_html}.py` | `test/offline/test_guard_report_masking.py` | BLOCK/REVIEW sections suppressed |
| REQ-E-06 | `src/tradingagents/resume.py` | `test/offline/test_resume.py` | attempts / locator / manifest publish |
| GOV-E-01 | baseline freeze | `docs/evaluation/baseline.md`, `env.txt`, `git show b5d2f67` | — |
| GOV-E-02 | `scripts/check_test_approval.py` | `test/offline/test_ci_gates.py`, `docs/approvals.yaml` | CI gate |
| GOV-E-03 | `.github/workflows/ci.yml`, `check_dependencies.py` | `test/offline/test_ci_gates.py` | CI gate |
| GOV-E-04 | `scripts/check_req_schema.py` | `test/offline/test_ci_gates.py` | CI gate |
| GOV-E-05 | `.github/workflows/ci.yml` (semantic-eval) | `test/offline/test_semantic_eval.py` | CI gate (advisory) |
| GOV-E-06 | `.github/workflows/ci.yml`, README | CI status | CI gate |
| GOV-E-07 | `scripts/check_ai_use_log.py` | `test/offline/test_ci_gates.py`, `docs/ai-use-log.yaml` | CI gate |
| GOV-E-08 | `scripts/check_permission_sync.py` | `test/offline/test_permission_sync.py`, `opencode.jsonc` | — |
| GOV-E-09 | branch protection | GitHub settings | — |
| GOV-E-10 | README delivery content | README.md | — |
| GOV-E-11 | AI-use log maintenance | docs/ai-use-log.yaml | CI gate (GOV-E-07) |
| SEC-E-01 | branch protection: another person's review | GitHub settings | — |
| GOV-E-12 | E plans + `docs/plans/E/REQ-LINAN-USAGE.yaml` | — | — |
| GOV-E-13 | E offline suites | `test_run_recorder.py`, `test_ci_gates.py`, `test_compare_runs.py`, `test_usage_window.py`, `test_guard_report_masking.py` | regression suite |

## Known gaps to resolve before submission

1. `test/offline/test_review.py` referenced by B-REQ-* does not exist.
2. A REQ-EV-* and D REQ-D-001…013 / INV-D1…8 are not in `requirements.yaml`.
3. Pending selectors (`C-P0x`, checkpoint preflight) are registry reservations, not test evidence.
4. Several E governance items have no runtime monitor (acceptable for governance, but state it).
