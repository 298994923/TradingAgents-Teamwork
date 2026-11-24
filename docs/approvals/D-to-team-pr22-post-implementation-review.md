# D → Team: PR #22 post-implementation independent review

Reviewer: Liu Kehong (Role D, Student ID: 60894001). Review date: 2026-11-24.
Character: **post-implementation review**, conducted after PR #22 was opened. This record
is dated the day it was actually performed; nothing here is backdated, and it is
explicitly distinct from any pre-implementation approval — because none exists (see §4).

## 1. Subject and lineage (verified)

- PR **#22** "Wire B prompt receipts through the runtime graph", author
  `tiantianzhenyouxie` (Role B), branch `codex/b-main-receipts` → main, +111/−20, 9 files.
- Published head `f196cd3` → descendant of `6ad01b8`; the latter carries tree
  `a2bb9a97…` and parent `1930bef`, **byte-identical tree to the jointly tested candidate
  `d81658d`** (verified via GitHub commit metadata: same tree hash, same parent).
  `f196cd3` adds only `docs/ai-use-log.yaml` changes (verified locally: the whole
  6ad01b8→head diff is that one file, +11). Src is unchanged by the descendants.
- My constructor-adaptation decision of 2026-11-23/24 (scoped to tree `a2bb9a97` at
  parent `1930bef`, or a descendant leaving the constructor region byte-identical)
  therefore **covers this published head**. The printed constructor diff matches the
  reviewed context exactly: `on_prompt=None` after `callbacks`, forwarding to `GraphSetup`.

## 2. Technical findings (all verified against the actual diff)

Pinned bytes: `tests/test_graph_end_to_end.py` = SHA-256
`98555b50132447a2ebf440da396e9b18c117b119fb5d61314e1c07382f41d5c7`;
new module `src/tradingagents/agents/prompt_receipts.py` = SHA-256
`93acd9c777fb7a504fccfb5fbe3c8f462622fce0fc272e9b78ce40608756392c`.

1. **Receipts capture the actual sent prompt.** The observer records two digests:
   `input_sha256` over the exact prompt string at send time, and
   `prompt_hashes["b.<role>"]` over the static template. The latter links each receipt to
   Role B's stable-ID constraint register (RC-1), closing the loop my 2026-11-22 review
   required. The PR body's claim "record the SHA-256 of the UTF-8 prompt at each
   application-level model send, including manager fallback" is implemented, not aspirational.
2. **The two added tests are genuine and strong.** `test_graph_prompt_receipts` is
   parameterized over normal and manager-fallback paths; it asserts the exact receipt role
   sequence and, decisively, that every reported `input_sha256` equals the SHA-256 of the
   prompt string the scripted model actually received. Observer-view equals model-view.
   Purely additive to the pre-existing e2e suite (41 lines added, zero deletions).
3. **Opt-in default is inert.** `on_prompt=None` ⇒ observer returns `None` ⇒ no
   attachment; the entire legacy suite runs the default path and CI tests/lint/schema/ai-use-log
   are green.
4. Non-blocking notes: (a) `state["investment_debate_state"]` is hard-indexed in the
   observer — safe for current research-role usage, revisit before any wider attachment;
   (b) the `legacy_prompt_observer` naming correctly scopes this to the legacy path — V2
   receipt forwarding remains subject to the adopted V2 addenda; (c) the upstream-suite
   case count will grow by 2 (1412→1414 expected) — zero-regression claims must state
   the new count honestly.

## 3. Custody observations (favorable)

The original commit was authored by the Codex agent (2026-11-24 18:15 local); Role B
re-committed it verbatim under his own identity one hour later (same tree, same parent),
then added an AI-use-log confirmation commit at 19:32. This is the AI-use discipline the
course requires, executed visibly.

## 4. Gap (confirmed, not created by this review)

- The automated gate `scripts/check_test_approval.py` correctly reports: 6 changed src
  files with no approval record (research_manager, prompt_receipts, bear_researcher,
  bull_researcher, structured, setup). Repo-wide search confirms **no pre-implementation
  test/scope approval record exists for this work** (docs/approvals.yaml, docs/approvals/,
  no docs/plans/B/). This review is the first independent review of these bytes on record.
- Additional batch condition from my signed keyed-regression scope confirmation: the
  receipts control test `test/offline/test_checkpoint_graph_prompt_receipts.py`
  (SHA-256 `d86e8277…`) must land in the same batch as this wiring. It is not among
  PR #22's nine files; until it lands, the #18 final 41-case gate stays open.

## 5. Verdict and conditions

**APPROVE (scoped, post-implementation), with three merge conditions:**

1. Team lead (E) rules whether post-implementation approval records satisfy the course
   requirement; if yes, per-file records are registered **dated 2026-11-24**, each stating
   "registered post-implementation; process deviation logged; basis: this review".
   Proposed signer split (non-author rule): Role D signs the four safety-boundary files
   (prompt_receipts, research_manager, bull/bear researchers) citing this document;
   Role C signs structured.py and setup.py (C owns both and already approved the code).
2. The receipts control test (`d86e8277…`) lands in the same merge batch, or E explicitly
   accepts an immediate follow-up PR landing before the #18 gate run.
3. After merge, zero-regression is re-run on main and recorded with the updated case count.

If E rules post-implementation records insufficient, the honest options remain: B
registers the deviation himself and E grants a documented exception, or the team defines
the corrective course — in no case may any date be backfilled.

## Signature
Reviewer (Role D): Liu Kehong (Student ID: 60894001)
Date: 2026-11-24
Declaration: I have independently verified the review conclusions above, endorse them, and sign as the responsible reviewer.
Signature: Liu Kehong
