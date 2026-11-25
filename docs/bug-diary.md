# Bug diary — findings, catches and fixes (Role D log)

Actual discovery dates; each entry: what broke (or nearly did), how it was caught,
how it was resolved, the rule that came out of it.

BD-01 Fixture contradiction (2026-11-22). d7-lattice fixture expected PASS where
INV-D4 requires REVIEW_TERMINAL. Caught at pre-implementation review; fixed with
independent cross-check. Rule: fixtures are code, not gospel.

BD-02 Contract example that lied (2026-11-22). v1.0 documented REVIEW for
validate(ABSENT, None); real code returns BLOCK/MALFORMED. Caught by Role C. Fixed in
v1.1 with caller-construction rule + revision history. Rule: contracts cite executable truth.

BD-03 Import reds hiding assertion reds (2026-11-22). Three tests red only via
ImportError. Noted at approval; re-run to assertion level once symbols exist.

BD-04 The #19 hash standoff (2026-11-23). Two digests for one file (English draft vs
original). Both pinned separately, each approved for its own content. Rule: one hash,
one version, one purpose.

BD-05 Same-batch control missing (2026-11-24). Wiring PR carried no receipts control
test required by signed scope confirmation; caught at file-list review; control later
landed and hash-verified at the final gate. Rule: signed conditions check against the merge.

BD-06 D's own hash transcription error (2026-11-25). Ruling cited 63 hex chars — one
digit dropped. Caught by Role C; canonical digest confirmed; dated correction attached;
original untouched. Rule proven: the protocol binds the signers too.

BD-07 Reported merger vs merged_by (2026-11-25). Adoption record said contract owner
merged #32; metadata showed author self-merge. Caught by Role C; dated correction
record; procedure updated — merged_by is machine-verified before recording.

BD-08 Placeholder trap (2026-11-25). Design stores a thread under an empty run key as
bait; naive recomputation would return a foreign identity. Caught in test review;
blank run IDs rejected before any I/O, whitespace variants included.

BD-09 Sidecar double-write hazard (2026-11-25). Writer marks publication only after the
manifest link; a later SidecarError can trigger a second terminal write and mask the
first. Open with Role E; capture-enabled stays off meanwhile.

BD-10 F811 full-tree lint gap (2026-11-25). CI lint green (changed files) while full
tree reports 2 pre-existing F811. Open with Role C. Rule: know your tool's scope.

Recorder: Liu Kehong (Role D, 60894001), 2026-11-25.

## Role C — Terminal reporting defect

**Contributor:** LiChengzhi (61023334).

**C-BD-01 — Successful-run completion marker missing** (public contract and fix recorded 2026-11-25). Normal unguarded V0/V1 runs could reach the final decision but leave the manifest's `stop_reason` null. Scripted CLI verification exposed the missing marker while preserving guarded and exception cases as controls. [PR #32](https://github.com/298994923/TradingAgents-Teamwork/pull/32) defined the narrow completion semantics before [PR #37](https://github.com/298994923/TradingAgents-Teamwork/pull/37) added the terminal state-writing boundary without changing the recorder or Guard. Rule: verify the successful outcome and the cases where the marker must remain absent; do not use `completed` as a generic interpretation of null.

BD-11 The register keeper self-merged (2026-11-25). PR #49 (Role D's own records) was
merged by its author (Lynn22-git, per commit metadata) — tenth self-merge, first by the
register's keeper, caught by Role D's own merged_by sweep minutes later. Self-registered
on the PR with actual date; OI-01 updated to ten. Rule closing the loop: the register
binds the registrar first.
