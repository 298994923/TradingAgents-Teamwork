# Registration-r8 capture trace update

Prepared against `main@303c6d1bb9b1a81b89962d13fa7fbd6b7627b1e9`.
The existing 25 targets are preserved. This PR proposes the two C-owned targets
below; adoption will be established by the actual registration merge, separately
from producer implementation and CLI acceptance. Earlier trace records below
retain their dated baseline and evidence scope.

| Canonical ID | Owner | Independent fit observation | Threshold |
|---|---|---|---|
| REQ-C-CAP-01 | C | Selected analysts plus optional Memory Log join before actual registration/publication; publication precedes Bull and usable reference exposure | zero barrier/order/reference violations |
| INV-C-CAP-01 | C | Real destination/save failure preserves original cause, starts no Bull, produces no decision/usable reference, and keeps reserved ID/null in failure manifest and sidecar | zero propagation/execution/reference/identity violations |

Both use operator `eq`, threshold `0`, but have separate violation metrics and
independent success/failure assertions. CAP-01 is not an alias of A's artifact
oracle IDs, CKPT-01 lifecycle or CKPT-02 preflight. No provisional capture IDs
were supplied; canonical self-mappings add no invented temporary labels.

## Fixed test binding

C confirmed both r8 mappings in `C-to-A-fresh-evidence-capture-test-binding.md`
on 2026-11-25 (source SHA-256 `88ca5a599b83521806dfe63cda1e1b655aeed7922af59d08efa53eace38d2c4f`).
A received the original test and statically verified its SHA-256:
`6867469406558a474ebd236df4f1e81a50a445389f3c348687a5f50cebeb7396`.

C's intended repository path is `test/offline/fresh_evidence_capture/test_fresh_evidence_cli_review.py`.
This remains a planned C delivery location: the file is not on the pinned main,
and C reports no source commit yet. These are concrete future-path bindings,
not a claim that the test is currently available in the repository.

| Canonical ID | Exact pytest selector |
|---|---|
| REQ-C-CAP-01 | `test/offline/fresh_evidence_capture/test_fresh_evidence_cli_review.py::test_fresh_capture_v0_v1[v0-2]` |
| REQ-C-CAP-01 | `test/offline/fresh_evidence_capture/test_fresh_evidence_cli_review.py::test_fresh_capture_v0_v1[v1-1]` |
| INV-C-CAP-01 | `test/offline/fresh_evidence_capture/test_fresh_evidence_cli_review.py::test_save_failure_aborts_before_bull` |

The original test, `assertions.py` and `inputs.json` were supplied together;
the two support assets are intended to sit beside the test without changing its
imports or fixture loading. Their received SHA-256 values are:

- `assertions.py`: `1ed0a6e47c492962ffe6c629b8a1002a54bb7f86546e894ccf3fa5261af0e7c6`.
- `inputs.json`: `36380cdfb4e9ef5049edc5b3a45c62380d626d03280eb0bb3fccbaf80981bdb9`.

Coverage limit: the failure selector injects an actual publication/save error.
It does not independently exercise destination rejection, which remains within
the invariant's required behavior. The capture-off compatibility control is
`test_capture_off_preserves_v1`; it is not an additional capture-success case.
C reports the prior test-first result as one passing capture-off control and
three expected failures at the missing capture interface. This is C-reported
historical evidence, not a new run by A. A checked the received bytes and test
structure only. Producer delivery and runtime acceptance remain outstanding.

The same fixed file may verify both targets. Record path + actual function/
parameter selector + full hash in this trace and the reviewed integration plan;
do not edit its provisional docstrings, assertions or bytes merely to add the
formal IDs. A test text change would require separate review under D's process.

C reports D-to-C-fresh-evidence-implementation-approval.md approves the source/
test scope subject to Evidence contract adoption. That original approval is not
supplied here. After preparation, PR #46 adopted the fresh V0/V1 capture contract
in `docs/contracts/evidence.md`, commit
`735152116e7f094b6c8890f11c1bde4633c7a4b5`, merged as
`543aad0d745cd25584ecb765deac1904d8dea86e`. This registration was rebased onto
that merge. Contract adoption is now recorded; this creates no approval or
signature and does not establish producer implementation or runtime acceptance.

## Source and scope

Source: C-to-A-fresh-evidence-capture-traceability.md, SHA-256
`102c5e87673fae65896eff8b833e8471184dd631f2719c86f66995cc35035cb0` (English transcription in the source record).
The unchanged five-field envelope and existing A oracle remain applicable to
artifact checks. C owns graph ordering/failure behavior; E owns reservation,
manifest and sidecar forwarding. Explicit recovery, checkpoint binding, V2 and
new governance decisions remain outside this slice.

## Preserved earlier trace history

# Registration-r7 trace and publication status

Publication baseline: `main@e5897e87345339d1e9f7c863bbbe09d65b0b8038`.
The previous 23 requirement targets were adopted through PR #24, merge
`7c9d2b2e0d7c548b103b511f6a3cdeb93a2cbc67`. This PR proposes two additional
explicit-preflight targets. Registry adoption is separate from implementation
acceptance. Current availability is checked statically below; no tests were run.
Historical counts and approval-record statements keep their original scope.
Original requirement meanings, aliases and signed test bytes are preserved.

## REQ-C-01

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-01`

- `test/offline/test_execution_policy.py::test_same_input_scales_with_budget`
- `pending-whole-graph-test:C-P01-2-unit-review-stop`
## REQ-C-02

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-02`

- `test/offline/test_execution_policy.py::test_denied_call_preserves_reservation_and_is_not_invoked`
- `test/offline/test_execution_policy.py::test_t_p1_failed_reservation_locks_the_terminal_state`
- `pending-whole-graph-test:C-P02-public-outcome`
## REQ-C-03

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-03`

- `test/offline/test_execution_policy.py::test_reservation_is_reported_separately_from_usage`
- `test/offline/test_execution_policy.py::test_missing_usage_is_unknown_not_zero`
- `pending-integration-test:C-P03-per-call-reconciliation`
## REQ-C-04

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-04`

- `pending-owner-test-reference:C-P04-whole-graph-eligibility-progress-cap`
## REQ-C-05

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-05`

- `tests/test_graph_end_to_end.py::test_an_interrupted_run_resumes_from_its_checkpoint`
- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_signature_distinguishes_preset_at_equal_depth`
- `pending-owner-test-reference:C-P05-compatibility-and-checkpoint-preservation`
## REQ-C-06

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-06`

- `tests/test_graph_end_to_end.py::test_a_full_run_reaches_a_logged_decision`
- `tests/test_graph_end_to_end.py::test_an_interrupted_run_resumes_from_its_checkpoint`
- `test/offline/test_v1_fixed_pruning.py::test_omitted_variant_keeps_default_route`
- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports`
## REQ-C-FR-01

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-fr-01`

- `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports`
## INV-C-FR-01

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-fr-01`

- `test/offline/test_v1_fixed_pruning.py::test_omitted_variant_keeps_default_route`
- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports`
## INV-C-FR-02

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-fr-02`

- `test/offline/test_v1_fixed_pruning.py::test_rejected_variant_has_no_construction_side_effects`
## INV-C-FR-03

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-fr-03`

- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_signature_distinguishes_preset_at_equal_depth`
## A-EV-08

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/contracts/evidence.md`

- `test/offline/test_evidence_artifact_keys.py::test_valid_conversion_and_both_round_trips`
- `test/offline/test_evidence_artifact_keys.py::test_non_string_inputs_have_stable_errors`
- `test/offline/test_evidence_artifact_keys.py::test_noncanonical_snapshot_ids_are_rejected`
- `test/offline/test_evidence_artifact_keys.py::test_noncanonical_artifact_keys_are_rejected`
- `test/offline/test_evidence_artifact_keys.py::test_helpers_do_not_delegate_to_storage_or_identity_generation`
- `test/offline/test_evidence_artifact_keys.py::test_existing_fixture_and_apis_remain_compatible`
## REQ-D-007

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/plans/D/requirements-pack.yaml#REQ-D-007`

- `test/offline/test_constraints.py::test_inv_d6_dual_gate`
- `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_rating_block`
- `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_cap_block`
- `test/offline/test_safety_boundary.py::test_missing_gate_is_block`
- `test/offline/test_safety_boundary.py::test_verdict_lattice_is_monotonic`
- `test/offline/test_safety_boundary.py::test_review_is_non_executable_at_both_gates`
## REQ-C-CKPT-01

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-ckpt-01`

- `test/offline/test_checkpoint_graph_run_key.py::test_keyed_propagate_resumes_and_cleans_up_only_its_thread`
- `test/offline/test_checkpoint_graph_run_key.py::test_omitted_key_resumes_and_cleans_up_legacy_thread`
- `test/offline/test_checkpoint_graph_run_key.py::test_disabled_checkpointing_does_not_open_sqlite[omitted]`
- `test/offline/test_checkpoint_graph_run_key.py::test_disabled_checkpointing_does_not_open_sqlite[keyed]`
- `test/offline/test_checkpoint_graph_prompt_receipts.py::test_unkeyed_checkpoint_route_preserves_real_prompt_receipts`
## INV-C-CKPT-01

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-ckpt-01`

- `test/offline/test_checkpoint_graph_run_key.py::test_keyed_propagate_resumes_and_cleans_up_only_its_thread`
## REQ-C-STOR-01

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-stor-01`

- `test/offline/test_checkpoint_thread_identity.py::test_run_scoped_thread_id_is_repeatable_and_normalizes_ticker_case`
- `test/offline/test_checkpoint_thread_identity.py::test_distinct_run_keys_have_distinct_thread_ids`
- `test/offline/test_checkpoint_thread_identity.py::test_run_key_cannot_alias_a_legacy_signature_suffix`
- `test/offline/test_checkpoint_thread_identity.py::test_run_key_requires_keyword`
## INV-C-STOR-01

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-stor-01`

- `test/offline/test_checkpoint_thread_identity.py::test_legacy_thread_ids_with_omitted_run_key`
- `test/offline/test_checkpoint_thread_identity.py::test_legacy_thread_ids_with_empty_run_key`
- `test/offline/test_checkpoint_thread_identity.py::test_distinct_run_keys_have_distinct_thread_ids`
- `test/offline/test_checkpoint_thread_identity.py::test_run_key_cannot_alias_a_legacy_signature_suffix`
## REQ-C-STOR-02

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-stor-02`

- `test/offline/test_checkpoint_run_key_storage.py::test_keyed_lookup_returns_only_the_requested_step`
- `test/offline/test_checkpoint_run_key_storage.py::test_unknown_key_does_not_fall_back_or_delete_existing_threads`
## INV-C-STOR-02

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-stor-02`

- `test/offline/test_checkpoint_run_key_storage.py::test_unknown_key_does_not_fall_back_or_delete_existing_threads`
- `test/offline/test_checkpoint_run_key_storage.py::test_keyed_cleanup_removes_only_target_checkpoint_and_writes`
- `test/offline/test_checkpoint_run_key_storage.py::test_unkeyed_lookup_and_cleanup_still_target_legacy_thread`
## REQ-C-STOR-03

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-stor-03`

- `test/offline/test_checkpoint_exact_thread_lookup.py::test_exact_original_threads_exist_without_step_metadata`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_thread_does_not_use_nearby_threads`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_database_path_with_spaces_and_hash`
## INV-C-STOR-03

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#inv-c-stor-03`

- `test/offline/test_checkpoint_exact_thread_lookup.py::test_exact_original_threads_exist_without_step_metadata`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_thread_does_not_use_nearby_threads`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_database_does_not_create_parent`
- `test/offline/test_checkpoint_exact_thread_lookup.py::test_storage_errors_are_not_reported_as_absence`
## REQ-C-STOR-04

Status: registered target through PR #24; runtime verification is separate.
Source: `docs/req/sources/c-registration-2026-11-23.md#req-c-stor-04`

- `test/offline/test_checkpoint_exact_thread_cleanup.py::test_clears_only_original_thread_and_repeats_safely`
- `test/offline/test_checkpoint_exact_thread_cleanup.py::test_returns_true_when_only_one_table_has_target_rows`
## INV-C-STOR-04

Status: registered target through PR #24; runtime verification is separate.
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
that selection for this documentation update. The final selection has 41 cases when the real receipt control is included.
That test is now delivered through PR #21. The V1 approval record reports
41 passing on its refreshed candidate; A has not rerun it for this update.
This does not close explicit preflight or terminal-publication integration.
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
- ADR-006 was delivered through PR #19. PR #21 now delivers the selector
  implementation and the fixed-pruning and real receipt test files. Their
  signed hashes and the intended selectors are verified below. Existing
  approval records report 14 V1 and 41 checkpoint passes on a refreshed
  candidate; this documentation change does not re-execute those tests.
- PR #20 adds E's recorder, usage and recovery support. Module availability
  does not close REQ-C-03 per-call reconciliation or Evidence recovery acceptance.
- PR #23 delivers the research-budget addenda in ADR-004/execution-budget.md.
  It does not itself deliver adaptive routing or close REQ-C-01..04 graph tests.

## Approval attribution source boundary

Main already contains the Evidence approval entry transcribed from A's explicit
2026-11-24 confirmation that C completed this delivery's approval responsibilities.
No E approval is reopened and this PR does not alter any approval ledger.
C's earlier storage-adoption response separately references
C-to-A-evidence-approval-attribution-confirmation.md; that original is not in the
received local handoffs or this baseline. Its contents are not inferred. Any
subsequent attribution correction belongs to a separate, source-backed update.
The latest follow-up requests registry publication, not a new Evidence API.


## Explicit preflight: new registration targets

| Provisional ID | New canonical target | Existing-target relationship |
|---|---|---|
| REQ-C-LOCAL-CKPT-006 | REQ-C-CKPT-02 | Refines part of REQ-C-05; not an alias of STOR-03 or graph CKPT-01 |
| INV-C-LOCAL-CKPT-006 | INV-C-CKPT-02 | Distinct pre-storage identity rejection and read-only preflight boundary |

Status: proposed registration; C reports fixed tests pinned by D and seven red
cases because the entry point is absent. A has not received the original test
file, independently checked its hash/assertions, or rerun it. The six function
names below expand to seven cases according to C: the blank-run-ID function
covers empty and blank values. Exact pytest parameter IDs are not supplied.

Reported file: `test_explicit_checkpoint_preflight_main.py`.
Reported SHA-256: `37a21a84170343ad1536ae9851bdefa86f9e5c07ec86a6693b1b87dc41b0c51a`.
Repository-relative location: not supplied; do not invent a delivered path.
The registry uses explicit pending-owner references to retain the selectors.

| Target | Reported function | Status |
|---|---|---|
| REQ-C-CKPT-02 | `test_preflight_verifies_exact_original_database_and_thread` | C-reported red; original test pending |
| INV-C-CKPT-02 | `test_preflight_rejects_neighbor_identity_before_storage` | C-reported red; original test pending |
| INV-C-CKPT-02 | `test_preflight_rejects_missing_thread_without_using_neighbors` | C-reported red; original test pending |
| INV-C-CKPT-02 | `test_preflight_rejects_blank_run_id_before_storage` | C-reported red; original test pending |
| INV-C-CKPT-02 | `test_preflight_reports_absent_database_without_creating_it` | C-reported red; original test pending |
| INV-C-CKPT-02 | `test_preflight_propagates_database_errors` | C-reported red; original test pending |

Preflight validates the original caller target before graph execution. STOR-03
supplies lower-level exact lookup; CKPT-01 governs graph continuation/cleanup.
Neither existing entry covers all this new preflight contract, so two new
targets are proposed instead of silently broadening an existing entry.
Evidence APIs, raw acquisition, complete compatibility assessment and terminal
manifest publication are not changed. No fixed test text change is requested.

## Current fixed test fingerprints

| Delivered file | SHA-256 | Local check |
|---|---|---|
| `test/offline/test_v1_fixed_pruning.py` | `6b8b412a29f7af2fc03f1b5b531b75171b39c97b03e29c0acec2fe723b4e5099` | matches signed record |
| `test/offline/test_checkpoint_graph_prompt_receipts.py` | `d86e8277d8c640014295244c1d2cbf5b6a656e2e782ab204578c972dc933b643` | matches signed record |

## Intended selector availability at the publication baseline

These are static path/function checks, not newly executed tests. All original
50 unique script/test references now resolve. The preflight pending references
and the five pre-existing whole-graph/integration pending markers are separate.

| Intended reference | Availability |
|---|---|
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_clears_only_original_thread_and_repeats_safely` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_missing_database_does_not_touch_filesystem` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_returns_true_when_only_one_table_has_target_rows` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_schema_error_surfaces_without_creating_tables` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_exact_thread_cleanup.py::test_second_delete_failure_rolls_back_first_delete` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_database_path_with_spaces_and_hash` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_exact_original_threads_exist_without_step_metadata` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_database_does_not_create_parent` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_missing_thread_does_not_use_nearby_threads` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_exact_thread_lookup.py::test_storage_errors_are_not_reported_as_absence` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_graph_prompt_receipts.py::test_unkeyed_checkpoint_route_preserves_real_prompt_receipts` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_graph_run_key.py::test_disabled_checkpointing_does_not_open_sqlite[keyed]` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_graph_run_key.py::test_disabled_checkpointing_does_not_open_sqlite[omitted]` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_graph_run_key.py::test_keyed_propagate_resumes_and_cleans_up_only_its_thread` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_graph_run_key.py::test_omitted_key_resumes_and_cleans_up_legacy_thread` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_run_key_storage.py::test_keyed_cleanup_removes_only_target_checkpoint_and_writes` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_run_key_storage.py::test_keyed_lookup_returns_only_the_requested_step` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_run_key_storage.py::test_unkeyed_lookup_and_cleanup_still_target_legacy_thread` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_run_key_storage.py::test_unknown_key_does_not_fall_back_or_delete_existing_threads` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_thread_identity.py::test_distinct_run_keys_have_distinct_thread_ids` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_thread_identity.py::test_legacy_thread_ids_with_empty_run_key` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_thread_identity.py::test_legacy_thread_ids_with_omitted_run_key` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_thread_identity.py::test_run_key_cannot_alias_a_legacy_signature_suffix` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_thread_identity.py::test_run_key_requires_keyword` | delivered; function resolved where specified |
| `test/offline/test_checkpoint_thread_identity.py::test_run_scoped_thread_id_is_repeatable_and_normalizes_ticker_case` | delivered; function resolved where specified |
| `test/offline/test_ci_gates.py` | delivered; function resolved where specified |
| `test/offline/test_constraints.py::test_inv_d6_dual_gate` | delivered; function resolved where specified |
| `test/offline/test_evidence_artifact_keys.py::test_existing_fixture_and_apis_remain_compatible` | delivered; function resolved where specified |
| `test/offline/test_evidence_artifact_keys.py::test_helpers_do_not_delegate_to_storage_or_identity_generation` | delivered; function resolved where specified |
| `test/offline/test_evidence_artifact_keys.py::test_non_string_inputs_have_stable_errors` | delivered; function resolved where specified |
| `test/offline/test_evidence_artifact_keys.py::test_noncanonical_artifact_keys_are_rejected` | delivered; function resolved where specified |
| `test/offline/test_evidence_artifact_keys.py::test_noncanonical_snapshot_ids_are_rejected` | delivered; function resolved where specified |
| `test/offline/test_evidence_artifact_keys.py::test_valid_conversion_and_both_round_trips` | delivered; function resolved where specified |
| `test/offline/test_execution_policy.py::test_denied_call_preserves_reservation_and_is_not_invoked` | delivered; function resolved where specified |
| `test/offline/test_execution_policy.py::test_missing_usage_is_unknown_not_zero` | delivered; function resolved where specified |
| `test/offline/test_execution_policy.py::test_reservation_is_reported_separately_from_usage` | delivered; function resolved where specified |
| `test/offline/test_execution_policy.py::test_same_input_scales_with_budget` | delivered; function resolved where specified |
| `test/offline/test_execution_policy.py::test_t_p1_failed_reservation_locks_the_terminal_state` | delivered; function resolved where specified |
| `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_cap_block` | delivered; function resolved where specified |
| `test/offline/test_safety_boundary.py::test_dual_gate_trader_pass_then_pm_rating_block` | delivered; function resolved where specified |
| `test/offline/test_safety_boundary.py::test_missing_gate_is_block` | delivered; function resolved where specified |
| `test/offline/test_safety_boundary.py::test_review_is_non_executable_at_both_gates` | delivered; function resolved where specified |
| `test/offline/test_safety_boundary.py::test_verdict_lattice_is_monotonic` | delivered; function resolved where specified |
| `test/offline/test_v1_fixed_pruning.py::test_explicit_signature_distinguishes_preset_at_equal_depth` | delivered; function resolved where specified |
| `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports` | delivered; function resolved where specified |
| `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved` | delivered; function resolved where specified |
| `test/offline/test_v1_fixed_pruning.py::test_omitted_variant_keeps_default_route` | delivered; function resolved where specified |
| `test/offline/test_v1_fixed_pruning.py::test_rejected_variant_has_no_construction_side_effects` | delivered; function resolved where specified |
| `tests/test_graph_end_to_end.py::test_a_full_run_reaches_a_logged_decision` | delivered; function resolved where specified |
| `tests/test_graph_end_to_end.py::test_an_interrupted_run_resumes_from_its_checkpoint` | delivered; function resolved where specified |

## Role B requirements registration

The [B handoff](sources/B-trace-for-A.tsv) supplies the original identifiers,
statements, thresholds and reported evidence limits for B-REQ-01 through
B-REQ-12. The registry retains these identifiers directly. The verification
selectors come from the B coursework checkout reviewed on 2026-11-22.
They identify the historical checks and may differ from paths or test names
on main. This registration does not establish fresh runtime acceptance.

The handoff flagged follow-up evidence for strict historical citations
(B-REQ-04), manager-to-graph handoff (B-REQ-10), and pinned legacy prompt
and returned-state equivalence (B-REQ-11). Those observations are dated
to the handoff; this registration does not adjudicate later evidence.
