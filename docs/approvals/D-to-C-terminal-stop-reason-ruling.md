# D → C: V0/V1 terminal stop_reason — dated ruling

Re: `C-to-D-v0-v1-terminal-stop-reason-scope-confirmation.md` v0.1.
Decision date: 2026-11-25. Reviewer: Role D (60894001).
Baseline: main `18090cf71e886da1ca07401377509ac3d3964f46` (includes #21 and #26).
Pinned: `test_v0_v1_terminal_stop_reason.py` SHA-256
`7a47e4eac95f08aa6533889f8a751c59d13ea7115bb5fd358676272f63797415`; red run accepted as
described (2 expected missing-`completed` failures, 61 passes; current successful V0/V1
record `(null, null)`; exception path writes failure/null and retains the checkpoint;
real Guard BLOCK emits null, not `completed`; receipt digests match actual model inputs).
No production edits made pending this decision — correct.

## 1. ADR: no covering text for the value mapping — narrow addendum required first

The adopted RunEvent contract records that a run-level `stop_reason` field exists; it
does not adopt a value enumeration. `completed` for normal graph termination is new
normative content, so: no new ADR; **one narrow addendum to `docs/contracts/run-event.md`,
adopted via a docs PR before source work**, recording exactly:

- `completed` is written for a normal, unguarded final decision only: the run reached
  the Portfolio Manager final-decision edge, terminated without exception, and no guard
  stop intervened;
- the enumeration is open: additional values enter only by dated Role D ruling with
  their own pinned tests; no value is written speculatively — unknown dispositions
  remain null (null means "no adopted literal yet", never "fine");
- `stop_reason` is a single run-level slot whose writer depends on where execution
  stopped; writers are mutually exclusive per workflow variant — this slice adds only
  the terminal writer and does not touch the V2 scheduler/manager channels
  (`research_stop_reason`, manager-handoff `stop_reason` semantics unchanged);
- `guard_result` is never altered by this mechanism; E's writer and schema are untouched
  (E passively persists whatever state carries — as already built).

Byte-verify the addendum against these bullets, I sign, adoption SHA recorded; source
waits for that SHA. Same iron sequence as the V2 addenda and the resume addendum.

## 2. Approvals and express protected-path authorization

- The exact v0.1 plan and test bytes (`7a47e4ea…`) are **APPROVED** as pinned, within the
  boundaries set in §3–§4. v0.1 stays sealed; any case addition returns as v0.2 for
  pin review.
- **Express authorization, scoped and conditional**: `src/tradingagents/agents/state.py`
  for the single optional `stop_reason` channel (absent by default, no default
  initialization) and `src/tradingagents/graph/setup.py` for the Portfolio-Manager
  terminal wrapper that writes `completed` on the qualifying path, plus required
  imports. Conditions:
  1. addendum adoption SHA cited in the source PR;
  2. the approval record is placed **by a human** in `docs/approvals/` (you stated this
     requirement yourself — honored), citing this ruling, approver `60894001`, actual date;
  3. `docs/approvals.yaml` entries for both files inside the PR; fresh ai-use-log id,
     real `human_reviewed: true`;
  4. no reuse of prior Guard/V1/V2/receipt authorizations — agreed, this is a distinct
     grant for distinct files;
  5. drift rule: any byte change in Guard wiring, the V2 channels, receipts forwarding,
     or the pinned test at PR time → return to D;
  6. non-author merge, E's serial-merge discipline.

## 3. Completion boundary — yes, the narrow line

This slice marks **normal unguarded final decisions only**. Explicitly outside, staying
null (which is honest, not broken):
- unguarded `REVIEW` dispositions;
- guarded PASS (guard-lineage semantics get their own future slice and decision);
- exception paths (already correct as failure/null);
- anything a guard stop touched.

If you later want REVIEW or guarded-PASS values, bring them as a new pinned test with a
ruling request — do not stretch `completed` to cover them. `completed` means "reached
and terminated normally at the unguarded level", never "outcome quality was good".

## 4. Guard policy — keep null this slice; `validation_stopped` is NOT approved now

- Guarded non-PASS leaving `stop_reason` absent/null for this slice: **approved**. All
  guard semantics already travel in `guard_result` (verdict, reason_code, executability,
  rules chain); stop_reason must not duplicate, compete, or contradict them. Your red
  evidence already proves BLOCK emits null, not `completed` — exactly right.
- The literal `validation_stopped` remains **unapproved and unused** (you correctly
  refrained). Reserved for a future slice, and if adopted it will be scoped to guard
  terminal stops (BLOCK or terminal REVIEW that prevented the normal final decision),
  **never** guarded PASS, with precedence: a guard stop outranks any completed-family
  value, and `guard_result` is never modified. Own tests required at that time.

## 5. Verification program for the implementing candidate

Red on clean `18090cf…` (2 failures at missing `completed`, 61 controls green) →
implement → green on the same candidate: pinned terminal test, 14 V1, 41 checkpoint
(including receipts), full offline suite, ruff on changed files, `git diff --check`;
manifest/state pair assertions must pass through the real CLI finalizer and real writer
path as your evidence shows — no shim. One candidate, one run set, recorded once.

## Signature
Reviewer (Role D): Liu Kehong (Student ID: 60894001)
Date: 2026-11-25
Declaration: I have independently verified the review conclusions above, endorse them, and sign as the responsible reviewer.
Signature: Liu Kehong
