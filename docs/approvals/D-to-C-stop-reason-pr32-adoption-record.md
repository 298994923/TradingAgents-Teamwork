# Adoption record — run-event.md terminal stop reason addendum (PR #32)

Recorder: Liu Kehong (Role D, Student ID: 60894001). Record date: 2026-11-25.

## Facts

- PR #32 "Document the V0/V1 terminal stop reason", author Loaf-learning,
  reviewed head b660f63f7daa7079d5c4e2c8b337a2d32685785d; text confirmed verbatim
  against D-to-C-terminal-stop-reason-ruling.md §1 before merge
  (D-to-C-stop-reason-addendum-text-confirmation.md, 2026-11-25).
- Merged by the contract owner (Role E, reported) — non-author, the corrective
  pattern after the PR #21 deviation.
- Adoption merge SHA: 973f957 (Merge pull request #32 from
  298994923/c/v0-v1-terminal-stop-reason-contract), main fast-forward
  18090cf..973f957, docs/contracts/run-event.md +15 lines.

## Machine proofs (recorded)

1. File digest transition:
   - pre-adoption snapshot: eb17654815119b522e96b50df5aa19ceb126b78c726f838c5904e35e1eb9bb6a
   - post-adoption: d4dc383c2a7c2f07fe33108e52e57be8707bf270a1f845c8c748a08a10fd0f78
2. Equality of merged text with reviewed text: git diff b660f63f... main --
   docs/contracts/run-event.md produced no output on the synchronized main —
   the bytes on main are exactly the bytes reviewed and confirmed.
3. Addition-only: existing contract bytes preserved (fast-forward, +15 insertions,
   0 deletions).

## Consequence

The addendum is adopted normative text. The separately authorized source slice
(state.py optional stop_reason channel; setup.py terminal writer writing completed
under the exact qualifying conditions; pinned test
7a47e4eac95f08aa6533889f8a751c59d13ea7115bb5fd358676272f63797415)
is unblocked: its PR must cite adoption SHA 973f957, carry the human-placed
docs/approvals/ record and ledger entries citing the ruling chain, a fresh
ai-use-log id with real human_reviewed: true, run the signed verification program on
one candidate, and merge by a non-author. Guard semantics, V2 channels, E's writer
and schema remain untouched by that slice.

## Signature
Recorder (Role D): Liu Kehong (Student ID: 60894001)
Date: 2026-11-25
Declaration: I have independently verified the review conclusions above, endorse them, and sign as the responsible reviewer.
Signature: Liu Kehong
