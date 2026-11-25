# Registration-r7 current source record

Prepared against main@e5897e87345339d1e9f7c863bbbe09d65b0b8038 on 2026-11-25.
The prior 23 targets were adopted through PR #24. This PR proposes two new
explicit-preflight IDs and updates availability of already registered tests;
it changes no original 23 requirement objects, test bytes or approval records.

Source: C-to-A-explicit-checkpoint-preflight-traceability-confirmation.md.
SHA-256: `3ba1fa40c78e80e4c9117eb63afcb2b305692c2b3268a567594f29e6100f0459`.
C supplied the two provisional scopes, six function names, seven-case red
result and a fixed test hash. This is C-reported evidence; A did not receive
the original test bytes or independently rerun it. No new approval is invented.
ADR-004 is the governing recovery design reference; mapping registration does
not itself authorize a protected source change.

## REQ-C-CKPT-02

A assigns REQ-C-LOCAL-CKPT-006 to this new canonical target: explicit preflight
accepts only the expected original database/thread and returns the recorded
thread ID before graph execution. This supports part of REQ-C-05 and uses the
lower storage layer, without replacing either STOR-03 or CKPT-01.

## INV-C-CKPT-02

A assigns INV-C-LOCAL-CKPT-006 to this new canonical target: blank run IDs and
mismatched identities are rejected before storage; absence never falls back or
creates files; corruption remains an error; no graph execution or row mutation.
Selectors and reported test hash are preserved in evidence-registration-trace.md.
No test rewrite is requested, and the exact repository path remains to be supplied.

## Latest-main reconciliation

PR #22 delivers real prompt receipts; PR #21 delivers the V1 selector and fixed
test files. The two previously missing files now match their signed hashes.
The V1 approval record reports 14 V1 and 41 checkpoint passes on its candidate;
those are recorded historical results, not a new A test run or full preflight
acceptance. REQ-C-04 and D's compact-fit confirmation remain separate.

## Preserved earlier source history (superseded availability statements)

# Registration-r6 current status

Revision 2026-11-24-registration-r6 supersedes historical availability statements below.
Publication baseline: main@e16bf40209bca7179c161561189670c93187b8a1 (freshly fetched 2026-11-24).
No earlier source record, original label or signed test byte is rewritten.
PR #16 Evidence merge is verified as `61402afa740f0345fc5e36c8e338a1cc88d268b9`.
Storage PR #17 and graph PR #18 are delivered. Registry adoption is proposed
by this PR; it is distinct from software merge and runtime acceptance.

Latest source: C-to-A-checkpoint-storage-registration-adoption-follow-up.md.
SHA-256: bc263c696f63f8c956b44bfbf7d79c0bc136691079c63a79c403cf2c98dbb42b.
C confirms all eight STOR entries, preserves the four paired aliases/test hashes,
and requests a main-based registration PR/commit followed by its actual merge SHA.
The 23 registry entries and 23 storage cases are separate counts.
C reports D's written clarification: storage 23 + legacy 13 = 36; interim adds
4 graph cases = 40; final expected 41 awaits B's real receipt wiring.
The adopted graph approval record corroborates the intended selection; C's
reported pass is not presented as A's new test execution.
REQ-C-04, graph 004 remaining integration boundaries and terminal-publication
cleanup remain separately tracked. The compact D fit remains unconfirmed.

Evidence approval attribution is not changed here: A's explicit human confirmation
and current main ledger are retained. The additional attribution document named
in C's reply has not been received, so no conclusion is inferred from its title.

## Preserved earlier confirmation history

# C requirement confirmation source record

English registration transcription, revision 2026-11-23-registration-r2.
C confirms the ten mapping/requirement semantics from A-to-C-2026-11-23-r1.
This is owner confirmation, not shared-registry adoption or integration acceptance.
Original source: C-to-A-requirements-and-replay-questions.md; SHA-256: b0e9e1f33a0d82267b5fe0b12ec82899c7ff70b8b6778f94595e57c150a84b30.
The original feedback and signed tests/approvals are preserved externally; this
English record does not replace them. The candidate statements retain the earlier
owner-confirmed text. The package's embedded id-map still says confirmation pending;
C's newer narrative confirmation supersedes that historical status.

Signed V1 test text retains its original REQ-C-LOCAL-V1-001 and INV-C-LOCAL-V1-001/002/003
labels and SHA-256 6b8b412a29f7af2fc03f1b5b531b75171b39c97b03e29c0acec2fe723b4e5099.
C's previously reported candidate graph hash remains
fefce348c01c29f72e70b0be4e6645e8e9e77496148b718e36f40c76b43a0274,
not proof of a current committed graph version.

## REQ-C-01

C confirms the existing functional obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## REQ-C-02

C confirms the existing functional obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## REQ-C-03

C confirms the existing functional obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## REQ-C-04

C confirms the existing functional obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## REQ-C-05

C confirms the existing functional obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## REQ-C-06

C confirms the existing functional obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## REQ-C-FR-01

C confirms the existing functional obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## INV-C-FR-01

C confirms the existing invariant obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## INV-C-FR-02

C confirms the existing invariant obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## INV-C-FR-03

C confirms the existing invariant obligation and canonical mapping.
See aliases.json for preserved source labels and evidence-registration-trace.md
for exact selectors, partial coverage and missing acceptance.

## Current follow-up source

C confirms the explicit pending-marker convention for REQ-C-04 and the two
LOCAL-CKPT-004 lifecycle/isolation candidate aliases. Source follow-up SHA-256:
0908a06d9de9275d0b9e58c0fefff8bc2717da34e9dd2b9e27b2864c72b2f66c.
Main-based registration candidate revision 2026-11-23-registration-r4; no adoption claimed.

## REQ-C-CKPT-01

Saved-input keyed continuation, successful lifecycle cleanup, disabled-checkpoint
no-SQLite and legacy receipt controls. Exact signed scope is in C's embedded v0.1
plan and D ruling. Omitted and empty have distinct evidence; None is not promised.

## INV-C-CKPT-01

Sibling/legacy isolation and compatibility-namespace preservation. Lower storage
identity, exact lookup and atomic cleanup remain distinct obligations.

## REQ-C-STOR-01

C confirms this storage mapping and fixed-test semantics. Implemented through
PR #17; compact entry remains proposed for registry adoption. See trace for
exact selectors/hashes, scope separation and caller obligations.

## INV-C-STOR-01

C confirms this storage mapping and fixed-test semantics. Implemented through
PR #17; compact entry remains proposed for registry adoption. See trace for
exact selectors/hashes, scope separation and caller obligations.

## REQ-C-STOR-02

C confirms this storage mapping and fixed-test semantics. Implemented through
PR #17; compact entry remains proposed for registry adoption. See trace for
exact selectors/hashes, scope separation and caller obligations.

## INV-C-STOR-02

C confirms this storage mapping and fixed-test semantics. Implemented through
PR #17; compact entry remains proposed for registry adoption. See trace for
exact selectors/hashes, scope separation and caller obligations.

## REQ-C-STOR-03

C confirms this storage mapping and fixed-test semantics. Implemented through
PR #17; compact entry remains proposed for registry adoption. See trace for
exact selectors/hashes, scope separation and caller obligations.

## INV-C-STOR-03

C confirms this storage mapping and fixed-test semantics. Implemented through
PR #17; compact entry remains proposed for registry adoption. See trace for
exact selectors/hashes, scope separation and caller obligations.

## REQ-C-STOR-04

C confirms this storage mapping and fixed-test semantics. Implemented through
PR #17; compact entry remains proposed for registry adoption. See trace for
exact selectors/hashes, scope separation and caller obligations.

## INV-C-STOR-04

C confirms this storage mapping and fixed-test semantics. Implemented through
PR #17; compact entry remains proposed for registry adoption. See trace for
exact selectors/hashes, scope separation and caller obligations.
