# Local handoff self-check

Owner approved S10 in the chat. This is a local handoff. No team PR, independent review signature, merged central trace matrix or recorded demo video is claimed.

| Acceptance | Test | Evidence |
|---|---|---|
| Blind opening | test_researcher_actual_prompts | S7 leak counts 2/2 legacy and 0/2 collaboration |
| Target exists | test_claim_validation; test_researcher_actual_prompts | S9 target_hit 6/6 |
| Valid evidence | test_claim_validation | S9 valid_evidence 30/30 |
| Bounded repair | test_repair_once | Offline positive and negative cases; no live attempts |
| Hard constraint retained | test_budget_boundary_and_compaction | S9 constraint_retention 3/3 |

Trace candidates for A: B-REQ-01/02 -> researcher actual prompts; 03/04 -> claim validation; 05 -> repair; 06/07/08 -> budget boundary and impossible budget; 09 -> fingerprint and dedup; 10 -> manager decision; 11 -> S7 comparison and legacy-equivalence record; 12 -> metrics placement and S9 manifests. Field and code references are in review-context.md. The S7 worktree was removed. Runtime outputs are local evidence and excluded from version control. The team AI-use log receives its per-PR entry when an actual PR exists.

Residual items: (1) C/D/E interface and metrics sign-off plus team merge, (2) student confirmation of reflection and final video, (3) limited live fixture coverage, including zero repair attempts. Team-owned pre-existing files include Chinese text; B-authored submission prose is English. Transcript preserves original conversation language.

Final team-layout regression: 1453 passed, 1 skipped, 1 deselected, 24 warnings, 100 subtests passed in 10.50s. See local-records/final-regression.log. Reconciled all twelve S9 input-token records to the archived manifests; total 4347.
