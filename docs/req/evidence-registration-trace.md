# Requirement and alias trace — registration-r3

Revision 2026-11-23-registration-r3. This record describes pre-merge proposal status,
not shared adoption or completed acceptance. Prepared against the inspected
integration@a61b7b587169bcfb20300be1b95f721e1a496caa on docs/a-requirements-registration.
The registry and schema still match the seed used by r2; unrelated entries are
preserved. The four-file documentation PR records adoption separately.

C confirms all ten meanings/mappings, including the workflow invariant semantics.
That request is closed. Original source/signed test IDs and hashes stay intact;
aliases are recorded separately in aliases.json, not extra requirement fields.
The latest narrative confirmation supersedes embedded historical pending labels.

## Ten C entries

### REQ-C-01

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE**.

- `test/offline/test_execution_policy.py::test_same_input_scales_with_budget`
- `pending-whole-graph-test:C-P01-2-unit-review-stop`
### REQ-C-02

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE**.

- `test/offline/test_execution_policy.py::test_denied_call_preserves_reservation_and_is_not_invoked`
- `test/offline/test_execution_policy.py::test_t_p1_failed_reservation_locks_the_terminal_state`
- `pending-whole-graph-test:C-P02-public-outcome`
### REQ-C-03

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE**.

- `test/offline/test_execution_policy.py::test_reservation_is_reported_separately_from_usage`
- `test/offline/test_execution_policy.py::test_missing_usage_is_unknown_not_zero`
- `pending-integration-test:C-P03-per-call-reconciliation`
### REQ-C-04

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE; verification pending**.

- `pending-owner-test-reference:C-P04-whole-graph-eligibility-progress-cap`
### REQ-C-05

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE**.

- `tests/test_graph_end_to_end.py::test_an_interrupted_run_resumes_from_its_checkpoint`
- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_signature_distinguishes_preset_at_equal_depth`
- `pending-owner-test-reference:C-P05-compatibility-and-checkpoint-preservation`
### REQ-C-06

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE**.

- `tests/test_graph_end_to_end.py::test_a_full_run_reaches_a_logged_decision`
- `tests/test_graph_end_to_end.py::test_an_interrupted_run_resumes_from_its_checkpoint`
- `test/offline/test_v1_fixed_pruning.py::test_omitted_variant_keeps_default_route`
- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports`
### REQ-C-FR-01

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE**.

- `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports`
### INV-C-FR-01

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE**.

- `test/offline/test_v1_fixed_pruning.py::test_omitted_variant_keeps_default_route`
- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_variants_use_fixed_depth_and_finish_reports`
### INV-C-FR-02

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE**.

- `test/offline/test_v1_fixed_pruning.py::test_rejected_variant_has_no_construction_side_effects`
### INV-C-FR-03

Owner-confirmed semantics/mapping: yes. Proposed inclusion: yes. Local candidate: yes.
Shared-branch adoption: no. Status: **STILL CANDIDATE**.

- `test/offline/test_v1_fixed_pruning.py::test_legacy_custom_depth_and_signature_are_preserved`
- `test/offline/test_v1_fixed_pruning.py::test_explicit_signature_distinguishes_preset_at_equal_depth`

## Coverage and pending verification convention

REQ-C-01's independent 3/2-unit final-review fixture is not the graph's 2-unit
zero-PM case. REQ-C-02 retains unaffordable-call/public-outcome coverage gaps;
REQ-C-03 retains per-call reconciliation; REQ-C-04 lacks actual adaptive graph
selectors/results. REQ-C-05's signature tests are partial, not actual checkpoint
rejection/resume/old-checkpoint acceptance. REQ-C-06's V1 fixed-pruning checks are
partial legacy compatibility, not budget/adaptive/performance acceptance.

Fixed-pruning tests retain explicit v0 Bull/Bear twice each, v1 once each,
omitted/None legacy caller depth including custom three, tested risk-depth-one
three-role path, unchanged caller/default config, rejection before tested
construction effects, and legacy/explicit signatures distinguished at equal depth.
Overlap is supporting evidence, not duplicate obligations or merged requirement IDs.

Existing pending-* verification strings are preserved verbatim as explicit
NON-EXECUTABLE gap sentinels; they are not invented tests. The compact schema
accepts arbitrary nonempty strings but cannot encode pending coverage semantically.
Do not interpret a schema pass as satisfying AGENTS.md's test-per-fit rule.
REQ-C-04 cannot be presented as test-complete; C must supply a real selector before
that rule is satisfied. Other entries retain concrete partial tests and their
pending cases; registration must not weaken the full statement to fit those tests.
The registry may record unfinished obligations with explicitly pending coverage;
registration does not make those obligations test-complete. Owners must supply
actual acceptance evidence before claiming completion.

## A-EV-08

ID retained: A-EV-08. Scope: canonical conversion/rejection, exact code/path,
purity and existing API/fixture compatibility. Code: evidence.py::artifact_key_for,
evidence.py::parse_artifact_key. Contract: docs/contracts/evidence.md, software API
addition 2026-11-22-helper-r1. The six exact functions are in the candidate registry.
Software is implemented and component-tested (128 combined component cases), now
available locally on feature/a-evidence@6fbd09fc68ddfcd67bdcc07b288916f517f6cb8f;
source SHA-256 717a24977fe8acad551470231dbb0f4a93cb79a40f2d250e0221123835dbaf88.
This does not establish formal requirement adoption or publication to integration.
A prepared/authorized the software scope; no separate formal human registry
adoption record is supplied. Status: STILL CANDIDATE, included in this local draft.
The inspected a61b7b5 target contains the component, contract and six helper test
functions. No code resubmission is requested. C/E graph, locator, archival/binding/manifest acceptance is separate.
Snapshot schema_version remains "1"; no implementation/schema change is proposed.

## D canonical relationship

Keep INV-D6 ↔ REQ-D-007. At local 42dbbec, invariants.md already records that
relationship; the shared compact registry has no REQ-D-007. Its proposed inclusion
copies the exact statement/type/priority from docs/plans/D/requirements-pack.yaml
(pack version 1, draft-for-review, 2026-11-21). Source statement is unchanged; the
compact adapter combines its two zero-violation fit criteria and links the actual
available dual-gate/monotonicity tests instead of planned nonexistent filenames.
This fit/format adapter needs D review and does not create a safety ID or adoption.
The inspected a61b7b5 target preserves the same D pack/invariant bytes as 42dbbec;
canonical relationship is verified locally. The compact-fit adapter still needs D
review. Status: STILL CANDIDATE.

## Current-target reference audit

On integration@a61b7b5, Evidence and execution-policy references resolve locally.
However, test/offline/test_v1_fixed_pruning.py is absent and the graph does not
expose workflow_variant. Twelve references into that file remain C-supplied
appendix evidence, not executable target-branch tests. C should identify the
actual V1 implementation/test branch or commit before whole-feature acceptance.
This is a target-version discrepancy; this documentation change neither imports
the missing feature nor weakens its requirements. Original test references are
preserved for reconciliation. No application tests were run for this document edit.

Historical 42dbbec and feature-branch references above identify original records,
not the current preparation base. Keyed-checkpoint lifecycle proposals remain
outside this registry pending full materials and owner confirmation.
