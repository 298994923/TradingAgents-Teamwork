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

---

## Role E — CLI and evidence-interface findings

**Contributor:** Nan Li (E, 60252993). Compiled 2026-11-25 from `bugfix/bug-diary.md` (BUG-E-001/002/003) and `bugfix/C-to-E-v1-cli-post-receipts-validation-follow-up.md`. The format below keeps D4's six fields where the source has them; the CLI variant findings are grouped as one entry with three confirmed root causes.

**E-BD-01 — CLI `--variant` default and effective-depth mismatch** (found by Role C's scripted CLI probe after PR #22; fixed 2026-11-24 by E, recorded here 2026-11-25).
- **Symptom:** Omitting `--variant` ran the v0 two-pair preset and changed the checkpoint signature even when the configured depth was three; explicit v1 was rejected before the graph was built; an explicit v0 run wrote manifest depth 3 while actually running two pairs. v2 rejection (zero model calls, no manifest) was correct and untouched.
- **Reproduction:** Typer probe of the public `analyze` command with scripted models, configured depth three: omitted/v0/v1/v2 cases compared actual behavior against required behavior (`C-to-E-v1-cli-post-receipts-validation-follow-up.md` §Observed).
- **Classification:** CLI interface defect — three confirmed root causes: (1) `main.py` defaulted `--variant` to `"v0"`, making omission indistinguishable from explicit v0; (2) `_reject_unavailable_variant(variant)` was called without the graph class, so v1 was refused before graph construction; (3) `_manifest_config_snapshot` used the input CLI config rather than effective graph settings.
- **Root cause:** request labels were conflated with effective settings; the legacy (no-flag) path had no distinct representation.
- **Fix:** default variant is `None` (legacy run); validation runs only for explicit values and only v2 is rejected at the public entry; `run_analysis` accepts `None`; `_effective_config()` overlays `max_debate_rounds`/`max_risk_discuss_rounds` from `graph.run_settings()` into both manifest writers; `_effective_manifest_variant` keeps `v0` as the legacy run_id label. Focused 66 passed; full offline 1904 passed / 1 skipped / 100 subtests; ruff and `git diff --check` clean. Risk routing and the 15 top-level RunEvent fields unchanged.
- **Invariant gap exposed:** "manifest settings must describe what actually ran" — the snapshot recorded the requested config, not the effective one. ADR-006 says only debate depth changes with the preset; a related test stub changed risk depth too and was flagged for revision (test-only, production copies only what `run_settings()` reports).

**E-BD-02 — Post-reservation initialisation failure left no failure manifest** (BUG-E-001; reported by Role C's closeout review 2026-11-25, fixed by E same day).
- **Symptom:** If `reserve_run_id()` succeeded but `_create_run_state` failed afterwards, the reserved run directory existed with no manifest — a silent failure with no terminal record.
- **Reproduction:** a graph whose `create_run_state` raises, through the real CLI `run_analysis`; reserved `runs/<run_id>/` has no `manifest.json`. Test `test/offline/test_evidence_boundaries.py::test_init_failure_after_reservation_writes_one_failure_manifest` written red first.
- **Classification:** error-handling gap at the CLI finalizer boundary.
- **Root cause:** `_create_run_state` was called outside the try/except that invokes `_finalize_run_manifest`, so the exception bypassed the single reserved id.
- **Fix:** moved initial-state construction inside the try; failures route through `_finalize_run_manifest(failure=...)` with the same writer/reservation; original error re-raised after one failure manifest; cleanup stays behind successful finalization. Full suite 2002 passed, ruff clean.
- **Invariant gap exposed:** every post-reservation outcome must have exactly one manifest at the reserved id; this was unstated.

**E-BD-03 — Sidecar failure after publication masked by a second terminal write** (BUG-E-002 / D's BD-09; reported by Role C, fixed by E 2026-11-25).
- **Symptom:** a `write_evidence_mode` / `write_prompt_receipts` failure after `write_manifest` published bubbled into the outer `except`, which called the writer again; the second `write_manifest` hit the no-overwrite guard and replaced the real sidecar error with "file exists" — a second terminal write and a masked cause.
- **Reproduction:** monkeypatch a sidecar writer to raise after publication; before the fix the visible error was the overwrite rejection and `write_manifest` was called twice. Tests `test_sidecar_failure_after_publish_no_second_write` / `_no_cleanup` written red first.
- **Classification:** error-masking defect in the failure path.
- **Root cause:** the writer had no "manifest already published" state, so the handler could not distinguish a pre-publication failure (write a manifest) from a post-publication sidecar failure (do not write again).
- **Fix:** writer exposes `is_published()` set when `write_manifest` returns; `_finalize_run_manifest` skips a second write and cleanup when published, re-raising the original error. Sidecar failures write `sidecar-error.json` and raise `SidecarError(cause=exc)` with the original chained; the manifest is immutable and untouched.
- **Invariant gap exposed:** one terminal manifest per run id, first error survives — the published/unpublished distinction was missing. (This is the implementation-level record of D's BD-09, which remains open at D's tracking level.)

**E-BD-04 — evidence_destination validated against an already-resolved root** (BUG-E-003; reported by Role C, fixed by E 2026-11-25).
- **Symptom:** `evidence_destination()` resolved the evidence root before checking containment; a symlinked `evidence` (or parent) pointing outside the configured tree made the resolved root itself the wrong anchor, so the check passed against the wrong tree. Dot-only run ids (`".."`) were also accepted.
- **Reproduction:** symlink the `evidence` directory (or a parent) outside `<results_dir>/runs/<run_id>/`, call `evidence_destination` with a canonical key; before the fix it returned an escaping path. Tests `test_symlinked_evidence_dir_escape_rejected_before_creation`, `test_symlinked_parent_run_escape_rejected`, `test_noncanonical_run_id_rejected` written red first.
- **Classification:** path-containment security defect plus input-validation gap.
- **Root cause:** resolution preceded anchoring; run id validation checked forbidden substrings rather than the recorder's `RUN_ID_PATTERN`.
- **Fix:** validate run id against `RUN_ID_PATTERN` plus dot-only rejection; lexically assert `results_root → run_root → evidence_root → destination` before resolving; reject escaping symlinks before creating directories; resolve and re-check containment inside the reserved run root. Canonical keys and normal directories unchanged.
- **Invariant gap exposed:** evidence artifacts must be written only inside the reserved run directory — the check previously anchored on a value a symlink could compromise.
