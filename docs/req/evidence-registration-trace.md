# Registration-r6 trace and publication status

Verified publication baseline: `main@e16bf40209bca7179c161561189670c93187b8a1`. Main was fetched on 2026-11-24.
This four-document PR proposes registry adoption. STILL CANDIDATE below is
the preparation status; merge history establishes adoption, not test acceptance.
A listed selector is an intended verification reference, not proof of a pass.
Unavailable selectors are explicitly classified in the availability table below.
C confirmation is complete; no registry adoption is inferred from software merge.
Original signed IDs/test bytes remain unchanged.

## REQ-C-01

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-01`

- `test/offline/test_execution_policy.py::test_same_input_scales_with_budget`
- `pending-whole-graph-test:C-P01-2-unit-review-stop`
## REQ-C-02

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-02`

- `test/offline/test_execution_policy.py::test_denied_call_preserves_reservation_and_is_not_invoked`
- `test/offline/test_execution_policy.py::test_t_p1_failed_reservation_locks_the_terminal_state`
- `pending-whole-graph-test:C-P02-public-outcome`
## REQ-C-03

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-03`

- `test/offline/test_execution_policy.py::test_reservation_is_reported_separately_from_usage`
- `test/offline/test_execution_policy.py::test_missing_usage_is_unknown_not_zero`
- `pending-integration-test:C-P03-per-call-reconciliation`
## REQ-C-04

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-04`

- `pending-owner-test-reference:C-P04-whole-graph-eligibility-progress-cap`
## REQ-C-05

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-05`

- `tests/test_graph_end_to_end.py::test_an_interrupted_run_resumes_from_its_checkpoint`
- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_signature_distinguishes_preset_at_equal_depth`
- `pending-owner-test-reference:C-P05-compatibility-and-checkpoint-preservation`
## REQ-C-06

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-06`

- `tests/test_graph_end_to_end.py::test_a_full_run_reaches_a_logged_decision`
- `tests/test_graph_end_to_end.py::test_an_interrupted_run_resumes_from_its_checkpoint`
- `test/offline/test_v1_fixed_pruning.py::test_omitted_variant_keeps_default_route`
- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports`
## REQ-C-FR-01

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-fr-01`

- `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports`
## INV-C-FR-01

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-fr-01`

- `test/offline/test_v1_fixed_pruning.py::test_omitted_variant_keeps_default_route`
- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports`
## INV-C-FR-02

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-fr-02`

- `test/offline/test_v1_fixed_pruning.py::test_rejected_variant_has_no_construction_side_effects`
## INV-C-FR-03

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-fr-03`

- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_signature_distinguishes_preset_at_equal_depth`
## A-EV-08

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/contracts/evidence.md`

- `test/offline/test_evidence_artifact_keys.py::test_valid_conversion_and_both_round_trips`
- `test/offline/test_evidence_artifact_keys.py::test_non_string_inputs_have_stable_errors`
- `test/offline/test_evidence_artifact_keys.py::test_noncanonical_snapshot_ids_are_rejected`
- `test/offline/test_evidence_artifact_keys.py::test_noncanonical_artifact_keys_are_rejected`
- `test/offline/test_evidence_artifact_keys.py::test_helpers_do_not_delegate_to_storage_or_identity_generation`
- `test/offline/test_evidence_artifact_keys.py::test_existing_fixture_and_apis_remain_compatible`
## REQ-D-007

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/plans/D/requirements-pack.yaml#REQ-D-007`

- `test/offline/test_constraints.py::test_inv_d6_dual_gate`
- `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_rating_block`
- `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_cap_block`
- `test/offline/test_safety_boundary.py::test_missing_gate_is_block`
- `test/offline/test_safety_boundary.py::test_verdict_lattice_is_monotonic`
- `test/offline/test_safety_boundary.py::test_review_is_non_executable_at_both_gates`
## REQ-C-CKPT-01

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-ckpt-01`

- `test/offline/test_checkpoint_graph_run_key.py::test_keyed_propagate_resumes_and_cleans_up_only_its_thread`
- `test/offline/test_checkpoint_graph_run_key.py::test_omitted_key_resumes_and_cleans_up_legacy_thread`
- `test/offline/test_checkpoint_graph_run_key.py::test_disabled_checkpointing_does_not_open_sqlite[omitted]`
- `test/offline/test_checkpoint_graph_run_key.py::test_disabled_checkpointing_does_not_open_sqlite[keyed]`
- `test/offline/test_checkpoint_graph_prompt_receipts.py::test_unkeyed_checkpoint_route_preserves_real_prompt_receipts`
## INV-C-CKPT-01

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-ckpt-01`

- `test/offline/test_checkpoint_graph_run_key.py::test_keyed_propagate_resumes_and_cleans_up_only_its_thread`
## REQ-C-STOR-01

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-stor-01`

- `test/offline/test_checkpoint_thread_identity.py::test_run_scoped_thread_id_is_repeatable_and_normalizes_ticker_case`
- `test/offline/test_checkpoint_thread_identity.py::test_distinct_run_keys_have_distinct_thread_ids`
- `test/offline/test_checkpoint_thread_identity.py::test_run_key_cannot_alias_a_legacy_signature_suffix`
- `test/offline/test_checkpoint_thread_identity.py::test_run_key_requires_keyword`
## INV-C-STOR-01

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-stor-01`

- `test/offline/test_checkpoint_thread_identity.py::test_legacy_thread_ids_with_omitted_run_key`
- `test/offline/test_checkpoint_thread_identity.py::test_legacy_thread_ids_with_empty_run_key`
- `test/offline/test_checkpoint_thread_identity.py::test_distinct_run_keys_have_distinct_thread_ids`
- `test/offline/test_checkpoint_thread_identity.py::test_run_key_cannot_alias_a_legacy_signature_suffix`
## REQ-C-STOR-02

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-stor-02`

- `test/offline/test_checkpoint_run_key_storage.py::test_keyed_lookup_returns_only_the_requested_step`
- `test/offline/test_checkpoint_run_key_storage.py::test_unknown_key_does_not_fall_back_or_delete_existing_threads`
## INV-C-STOR-02

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-stor-02`

- `test/offline/test_checkpoint_run_key_storage.py::test_unknown_key_does_not_fall_back_or_delete_existing_threads`
- `test/offline/test_checkpoint_run_key_storage.py::test_keyed_cleanup_removes_only_target_checkpoint_and_writes`
- `test/offline/test_checkpoint_run_key_storage.py::test_unkeyed_lookup_and_cleanup_still_target_legacy_thread`
## REQ-C-STOR-03

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-stor-03`

- `test/offline/test_checkpoint_exact_thread_lookup.py::test_exact_original_threads_exist_without_step_metadata`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_thread_does_not_use_nearby_threads`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_database_path_with_spaces_and_hash`
## INV-C-STOR-03

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-stor-03`

- `test/offline/test_checkpoint_exact_thread_lookup.py::test_exact_original_threads_exist_without_step_metadata`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_thread_does_not_use_nearby_threads`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_database_does_not_create_parent`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_storage_errors_are_not_reported_as_absence`
## REQ-C-STOR-04

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-stor-04`

- `test/offline/test_checkpoint_exact_thread_cleanup.py::test_clears_only_original_thread_and_repeats_safely`
- `test/offline/test_checkpoint_exact_thread_cleanup.py::test_returns_true_when_only_one_table_has_target_rows`
## INV-C-STOR-04

Status: STILL CANDIDATE. Included in local proposal.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-stor-04`

- `test/offline/test_checkpoint_exact_thread_cleanup.py::test_clears_only_original_thread_and_repeats_safely`
- `test/offline/test_checkpoint_exact_thread_cleanup.py::test_returns_true_when_only_one_table_has_target_rows`
- `test/offline/test_checkpoint_exact_thread_cleanup.py::test_second_delete_failure_rolls_back_first_delete`
- `test/offline/test_checkpoint_exact_thread_cleanup.py::test_missing_database_does_not_touch_filesystem`
- `test/offline/test_checkpoint_exact_thread_cleanup.py::test_schema_error_surfaces_without_creating_tables`

## Storage delivery and preserved boundaries

PR #17: implementation de8035b706f34498a9ff9159cef5c6b08ffc42f5; merge
9b44a7c7aadfd8ea976624add2d3368d8fbd4bd4. Latest C response supplies 20 function
selectors: 6/4/5/5 across four files, expanding statically to 6/4/6/7 cases (23).
The two legacy files tests/test_checkpoint_lifecycle.py and
tests/test_checkpoint_resume.py contribute 13 in the supplied historical run: 36
total. No pytest run is performed by this registration change.

LOCAL-CKPT-001/003/005/008 are storage groups. Graph LOCAL-CKPT-004 remains
REQ-C-CKPT-01 / INV-C-CKPT-01, with its signed test hashes retained from r4:
cffd4df67fc834d9d7a6d3f43705ebaeb84b10e263cd0d24d2291ea39a26d713 and
d86e8277d8c640014295244c1d2cbf5b6a656e2e782ab204578c972dc933b643.
Storage tests do not prove pending-Trader resume, graph cleanup sequencing,
manifest integration or graph lifecycle acceptance. Terminal manifest publication
before cleanup is a caller obligation requiring real integration evidence;
Evidence snapshot publication never authorizes checkpoint deletion.

The count wording is RESOLVED by C's latest response and the adopted
`docs/approvals/gate1-C-keyed-checkpoint-graph.md` transcription of
D-to-C-keyed-regression-scope-confirmation.md: 23 storage + 13 legacy = 36.
Interim keyed-graph acceptance adds 4 cases, for 40 on the same candidate.
C reports those 40 passing on its main@61402af-based candidate; A did not rerun
that selection for this documentation update. Final acceptance is an expected
41 only after the frozen real B prompt-receipt test can run on the same candidate.
That receipt test is not delivered at this baseline; no stub substitutes for it.
D's separate compact REQ-D-007 fit adaptation still needs confirmation.
INV-D6 ↔ REQ-D-007 remains canonical. REQ-C-04 retains its explicit pending
whole-graph verification marker. Other partial evidence/gaps remain in entries.

EvidenceError.code plus typed __cause__ remains the agreed loader boundary; E
distinguishes missing/unreadable/other I/O and validation categories. No new public
exception classes or Evidence API changes are requested. C/E real-loader and
recovery acceptance stays separate. C's Evidence approval is closed, not referred
to E for another review.


## Main delivery reconciliation

- Evidence: PR #16, merge `61402afa740f0345fc5e36c8e338a1cc88d268b9`;
  implementation `3512fffab4486bd532dd9104b70b76eca48288b6`.
  All six component files remain byte-identical to C's reviewed package.
- Storage: PR #17 and hashes above remain unchanged.
- Keyed graph: PR #18, merge `0760c5800912d1b570dd130d0d94c2c619cbf45a`.
  The four-case graph file is delivered with its signed hash; that delivery
  does not establish the separate locator/terminal-publication cleanup chain.
- ADR-006 was delivered through PR #19. Its presence is a design decision;
  the fixed-pruning test file referenced by the four FR entries is not yet
  delivered here. Retain its intended selectors and owner-confirmed semantics.
- PR #20 adds E's recorder, usage and recovery support. Module availability
  does not close REQ-C-03 per-call reconciliation or Evidence recovery acceptance.
- PR #23 delivers the research-budget addenda in ADR-004/execution-budget.md.
  It does not itself deliver adaptive routing or close REQ-C-01..04 graph tests.

## Approval attribution source boundary

Main already contains the Evidence approval entry transcribed from A's explicit
2026-11-24 confirmation that C completed this delivery's approval responsibilities.
No E approval is reopened and this PR does not alter any approval ledger.
C's latest response separately references
C-to-A-evidence-approval-attribution-confirmation.md; that original is not in the
received local handoffs or this baseline. Its contents are not inferred. Any
subsequent attribution correction belongs to a separate, source-backed update.
The latest follow-up requests registry publication, not a new Evidence API.


## Intended selector availability at the publication baseline

These are static path/function checks, not executed tests. Missing delivery
does not invalidate a requirement target or establish its acceptance.

| Intended reference | Availability |
|---|---|
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_clears_only_original_thread_and_repeats_safely` | available |
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_missing_database_does_not_touch_filesystem` | available |
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_returns_true_when_only_one_table_has_target_rows` | available |
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_schema_error_surfaces_without_creating_tables` | available |
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_second_delete_failure_rolls_back_first_delete` | available |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_database_path_with_spaces_and_hash` | available |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_exact_original_threads_exist_without_step_metadata` | available |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_database_does_not_create_parent` | available |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_thread_does_not_use_nearby_threads` | available |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_storage_errors_are_not_reported_as_absence` | available |
| `test/offline/test_checkpoint_graph_prompt_receipts.py::test_unkeyed_checkpoint_route_preserves_real_prompt_receipts` | pending delivery to main; owner-supplied intended reference |
| `test/offline/test_checkpoint_graph_run_key.py::test_disabled_checkpointing_does_not_open_sqlite[keyed]` | available |
| `test/offline/test_checkpoint_graph_run_key.py::test_disabled_checkpointing_does_not_open_sqlite[omitted]` | available |
| `test/offline/test_checkpoint_graph_run_key.py::test_keyed_propagate_resumes_and_cleans_up_only_its_thread` | available |
| `test/offline/test_checkpoint_graph_run_key.py::test_omitted_key_resumes_and_cleans_up_legacy_thread` | available |
| `test/offline/test_checkpoint_run_key_storage.py::test_keyed_cleanup_removes_only_target_checkpoint_and_writes` | available |
| `test/offline/test_checkpoint_run_key_storage.py::test_keyed_lookup_returns_only_the_requested_step` | available |
| `test/offline/test_checkpoint_run_key_storage.py::test_unkeyed_lookup_and_cleanup_still_target_legacy_thread` | available |
| `test/offline/test_checkpoint_run_key_storage.py::test_unknown_key_does_not_fall_back_or_delete_existing_threads` | available |
| `test/offline/test_checkpoint_thread_identity.py::test_distinct_run_keys_have_distinct_thread_ids` | available |
| `test/offline/test_checkpoint_thread_identity.py::test_legacy_thread_ids_with_empty_run_key` | available |
| `test/offline/test_checkpoint_thread_identity.py::test_legacy_thread_ids_with_omitted_run_key` | available |
| `test/offline/test_checkpoint_thread_identity.py::test_run_key_cannot_alias_a_legacy_signature_suffix` | available |
| `test/offline/test_checkpoint_thread_identity.py::test_run_key_requires_keyword` | available |
| `test/offline/test_checkpoint_thread_identity.py::test_run_scoped_thread_id_is_repeatable_and_normalizes_ticker_case` | available |
| `test/offline/test_ci_gates.py` | available |
| `test/offline/test_constraints.py::test_inv_d6_dual_gate` | available |
| `test/offline/test_evidence_artifact_keys.py::test_existing_fixture_and_apis_remain_compatible` | available |
| `test/offline/test_evidence_artifact_keys.py::test_helpers_do_not_delegate_to_storage_or_identity_generation` | available |
| `test/offline/test_evidence_artifact_keys.py::test_non_string_inputs_have_stable_errors` | available |
| `test/offline/test_evidence_artifact_keys.py::test_noncanonical_artifact_keys_are_rejected` | available |
| `test/offline/test_evidence_artifact_keys.py::test_noncanonical_snapshot_ids_are_rejected` | available |
| `test/offline/test_evidence_artifact_keys.py::test_valid_conversion_and_both_round_trips` | available |
| `test/offline/test_execution_policy.py::test_denied_call_preserves_reservation_and_is_not_invoked` | available |
| `test/offline/test_execution_policy.py::test_missing_usage_is_unknown_not_zero` | available |
| `test/offline/test_execution_policy.py::test_reservation_is_reported_separately_from_usage` | available |
| `test/offline/test_execution_policy.py::test_same_input_scales_with_budget` | available |
| `test/offline/test_execution_policy.py::test_t_p1_failed_reservation_locks_the_terminal_state` | available |
| `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_cap_block` | available |
| `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_rating_block` | available |
| `test/offline/test_safety_boundary.py::test_missing_gate_is_block` | available |
| `test/offline/test_safety_boundary.py::test_review_is_non_executable_at_both_gates` | available |
| `test/offline/test_safety_boundary.py::test_verdict_lattice_is_monotonic` | available |
| `test/offline/test_v1_fixed_pruning.py::test_explicit_signature_distinguishes_preset_at_equal_depth` | pending delivery to main; owner-supplied intended reference |
| `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports` | pending delivery to main; owner-supplied intended reference |
| `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved` | pending delivery to main; owner-supplied intended reference |
| `test/offline/test_v1_fixed_pruning.py::test_omitted_variant_keeps_default_route` | pending delivery to main; owner-supplied intended reference |
| `test/offline/test_v1_fixed_pruning.py::test_rejected_variant_has_no_construction_side_effects` | pending delivery to main; owner-supplied intended reference |
| `tests/test_graph_end_to_end.py::test_a_full_run_reaches_a_logged_decision` | available |
| `tests/test_graph_end_to_end.py::test_an_interrupted_run_resumes_from_its_checkpoint` | available |
