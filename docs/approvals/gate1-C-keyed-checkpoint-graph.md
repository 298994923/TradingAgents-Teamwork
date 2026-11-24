# Gate 1 Approval Record - C Keyed Checkpoint Graph

Independent reviewer and protected-path authorizer: Liu Kehong, Role D (60894001), signed 2026-11-23. This record transcribes D-to-C-keyed-checkpoint-ruling.md and D-to-C-keyed-regression-scope-confirmation.md. Both rulings remain the authoritative signatures.

Plan and scope: C-keyed-checkpoint-graph-review-package.md v0.1. Conditional authorization covers only the programmatic run_key lifecycle in src/tradingagents/graph/trading_graph.py: propagate(), checkpoint_scope(), begin_checkpoint(), _run_graph(), and clear_checkpoint_on_success(). Preserve compatibility signatures, exact unkeyed IDs and behavior, the disabled SQLite boundary, B's real receipt forwarding when present, and same-run Guard lineage. Restore executable=true only if that run's Portfolio Manager final gate issued PASS. Existing Guard opt-in scope remains separately approved.

Fixed tests (SHA-256):

- test/offline/test_checkpoint_graph_run_key.py: cffd4df67fc834d9d7a6d3f43705ebaeb84b10e263cd0d24d2291ea39a26d713
- test/offline/test_checkpoint_graph_prompt_receipts.py: d86e8277d8c640014295244c1d2cbf5b6a656e2e782ab204578c972dc933b643

ADR-004 and execution-budget.md were adopted in PR #14. Storage PR #17 merged at 9b44a7c7aadfd8ea976624add2d3368d8fbd4bd4. The formal red run at main 61402afa740f0345fc5e36c8e338a1cc88d268b9 used the actual merged storage files and unchanged trading_graph.py. It recorded 2 expected missing-run_key failures and 38 passes. Production port and green rerun remain pending at recording.

Interim acceptance is 4 graph + 23 storage + 13 legacy cases on one candidate. Once real B wiring is present, the same-candidate final gate adds the fixed receipt case for an expected 41. Use no receipt substitutes. Require Ruff and diff checks and send the pre-merge group notice specified in the ruling. The interim ledger lists the runnable keyed graph test alongside the separately approved Guard tests; add the frozen receipt test to the candidate and ledger when the final test can run.
