# Gate 1 Approval Record — D Safety Test Suite
Approver: Member B (independent reviewer)
Approval time: 2026-11-21 23:54 (Beijing time, UTC+8)
Conclusion: APPROVE
Subject: safety_cases.json + test_constraints.py + test_safety_boundary.py
Commit: 220510900ce8b9504f48e287fbeb21025398269f
Re-run: 88 collected, 66 assertion failures / 22 passed, matching red-run-04 item by item
Scope: guard tests only; main-graph dual-gate wiring, final-artifact interception, and green implementation to be verified separately
Attachment-commit consistency: SHA-256 hashes verified identical
Basis: B-门1复审-v2.md (B's gate-1 re-review, v2)
Recorded by: D, Liu Kehong (Student ID: 60894001), 2026-11-22

## Addendum 1: fixture reason-code correction (pre-implementation)
Change: d7-lattice-review-over-pass.expected_reason_code
  PRIOR_VERDICT_RETAINED -> REVIEW_TERMINAL (INV-D4: prior REVIEW terminal)
Reason: byte-identical inputs with d4-review-pm-terminal demanded different
  reason codes; deterministic guard cannot satisfy both (REQ-D-013).
Verdict/executable expectations unchanged; no other edits.
Re-run: 66 failed / 22 passed (red-run-05.txt)
New safety_cases.json SHA-256: <e6832b230e917ed905adbc77caae22a565c256f03f37a7e153990beed60c8d5e>
Re-approved by: Zhang Ruiqi, 2026-11-22, via group reply
Recorded by: D, Liu Kehong (60894001), 2026-11-22

## Addendum 2: guard-wiring test re-approval (6 tests)
Subject: test/offline/test_guard_wiring.py (6 opt-in guarded-mode tests)
Red: 6 failed against unwired code (wiring-red-01.txt) - proper red for right reason.
Compatibility: guard enforcement is opt-in (guard-enabled signal); legacy mode
preserves upstream baseline; upstream tests untouched.
Test SHA-256: <0a7e1dee4c62c66c53d02be5131a2e1305a577de06f7e37d5125d3fcfd8882ad>
Re-approved by: Zhang Ruiqi, 2026-11-22, via group reply
Recorded by: D, Liu Kehong (60894001), 2026-11-22