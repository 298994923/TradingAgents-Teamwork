# D → C: fresh Evidence capture — addendum vehicle, plan, tests, and three-path authorization

Re: `fresh-evidence-capture-architecture-addendum.md`, `C-fresh-evidence-implementation-review-plan.md` v0.2, `test_fresh_evidence_cli_review.py`.
Baseline: main `628f40cbd7fec539a93b5909d723a0c5a832efb2` (includes #42).
Decision date: 2026-11-25. Reviewer: Role D (60894001).

## 1. Addendum vehicle and text — APPROVED, with one incorporated sentence

Vehicle decision: the text is adopted **as a new section appended to
`docs/contracts/evidence.md`**, not as a standalone normative file — one domain, one
contract document, consistent with the run-event and V2 in-place precedents.

The proposed normative text is approved as written, with ONE sentence incorporated
before adoption (making rejection semantics normative, not plan-only):

> "Malformed activation payloads, missing or blank capture identifiers, and effective
> checkpoint enablement are rejected before any node execution or Evidence storage
> access."

The adoption PR must contain exactly the approved text plus that sentence; Role D
byte-verifies at adoption and records the adoption SHA. Source work cites that SHA.

## 2. Test bytes — reviewed and recorded

Reviewed bytes: `test_fresh_evidence_cli_review.py` SHA-256
`6867469406558a474ebd236df4f1e81a50a445389f3c348687a5f50cebeb7396` (248 lines, the copy
Role D inspected). Assertion spot-check found genuine verification throughout: node
order via the real `model.seen` sequence; receipts `input_sha256` compared against
actual scripted sends; exactly one evidence artifact under the destination; sidecar
strictly the two projected fields; capture clock read exactly once; capture-off case
asserts the four new channels are disjoint from state and no link/clock/destination
activity at all; save-failure case asserts error identity (`error is run.failure`),
`EvidenceError` with `IO_ERROR` and the injected `OSError` as `__cause__`, null
references across every stream chunk, null manifest outcome/stop_reason with the
reserved run ID retained, no Bull execution, and no `.evidence-*.tmp` residue.
Red evidence accepted as labeled: 1 pass (capture-off route intact), 3 expected
failures at the absent interface, 99 controls, honest disclosure of what has NOT yet
been demonstrated. Your SHA256SUMS remains the canonical pin; PR-time bytes are
re-verified mechanically against it.

## 3. Three-path scope — AUTHORIZED, conditions listed in §5

`state.py` (four optional channels, nothing seeded, no existing field/reducer changes),
`setup.py` (optional capture callable; same complete list-form barrier routed through
the capture node only on the opted-in path; every analyst subgraph and downstream
node/edge byte-intact), `trading_graph.py` (keyword-only `source_run_id`/`capture_context`,
private capture callable, separately compiled uncheckpointed workflow only inside the
opted-in `stream_run`; no `self.graph`/`self.workflow` replacement, no
`propagate`/checkpoint signature or lifecycle change, no stream-semantics change).

Ratified stop condition: the placeholder-omission/restore mechanism (item 2 of the
capture ordering) — if omitting selected report placeholders before fan-out requires
changing any other owner's outputs or readers, STOP and return for the narrower
contract decision. Activation is only ever an explicitly enabled context; an ID or
`evidence_mode` alone never activates.

## 4. Sidecar-after-manifest defect — not yours, but it gates the switch

The post-manifest `SidecarError` double-terminal-write hazard in
`_make_manifest_writer` is Role E's territory. Disposition: E handles it in a separate
slice with its own regression; C does not expand paths to fix it. Until E's fix lands
or E explicitly gates the combination, **capture-enabled runs remain an explicitly
off-by-default experimental path** — the flag may exist and be tested, but nothing
flips it on by default anywhere.

## 5. Acceptance conditions (ratifying your checklist, plus standing mechanics)

1. Adoption SHA present and cited; 2. on ONE candidate: all four pinned cases green
plus the targeted missing/blank/invalid trio, repeated disabled/enabled/disabled on a
reused graph instance, and entry-level refusal controls for capture+checkpoint (both
#42 checkpoints); 3. full controls green (99 + V1 14 + checkpoint 41 + receipts +
terminal + full offline), ruff/diff clean; 4. new REQ/INV ids from Role A covering the
barrier and null-on-failure behavior (A's oracle ids cover artifact assertions only —
no reuse); 5. per-file ledger entries citing this ruling chain appended (never
replacing), fresh ai-use-log id with real `human_reviewed: true`; 6. drift rule — any
movement in Guard wiring, receipt forwarding, stop_reason writer, checkpoint paths, or
any pinned test returns here; re-anchor if main moves again before PR (this baseline is
hot); 7. merge requires at least one non-author approval; merged_by machine-checked and
recorded at acceptance; 8. no backdating anywhere.

## Signature
Reviewer (Role D): Liu Kehong (Student ID: 60894001)
Date: 2026-11-25
Declaration: I have independently verified the review conclusions above, endorse them, and sign as the responsible reviewer.
Signature: Liu Kehong
