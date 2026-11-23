# Gate 1 Approval Record - C Checkpoint Storage

Independent reviewer: Liu Kehong, Role D (60894001). Signed on 2026-11-23 in D-to-C-checkpoint-storage-ruling.md. This record transcribes the signed decision.

Approved plan: C-to-D-checkpoint-storage-main-review.md v0.1. Approved source scope: src/tradingagents/graph/checkpointer.py only, SHA-256 f0e9b25f6c042fd56c503b8efe6c6a0843b6cf21b6a6fd84eb9254464d8456a0. Keyed identity and storage operations preserve legacy behavior. Exact lookup distinguishes absence from storage errors. Exact removal is atomic across both tables. The caller must supply the original database and thread and durably publish that run's terminal manifest before cleanup. Graph, CLI, and Evidence wiring are separate.

Approved test versions (SHA-256):

- test/offline/test_checkpoint_thread_identity.py: ffb9b616d48372fe5299234e73cb84497cf52396460621b1ec4e9c0b9b037e21
- test/offline/test_checkpoint_run_key_storage.py: 787e5c52fe125879329302272f597b39208bfe95e5e91e4c7bd7cfd2b6f9fb79
- test/offline/test_checkpoint_exact_thread_lookup.py: 44f51db5b978cbe7f4a5f5dc8ec162c570fdba0cb2750c48557b95f690106a36
- test/offline/test_checkpoint_exact_thread_cleanup.py: 1de250fd4c42857c17ebff3af9f6cd9a67b9315e903f73363e0489decc9c2831

The historical local prototype predates the signature. The subsequent isolated replay on main 2248d06ff8a4808a1b8ddeed21cba2f6959aa158 added the fixed tests before applying the pinned source patch. Baseline: 2 passed, 7 failed, 8 errors at missing storage interfaces. After application: 23 storage and 13 legacy tests passed. Full offline regression: 1624 passed, 1 skipped, 1 deselected and 100 subtests passed. Ruff and diff checks passed. Verified patch SHA-256: d6cdb09296da2f849e93d05950e682b4b4cf569546de15dfa85c8be9c3c27f39.

ADR-004 and the execution budget contract were adopted in PR #14. Follow D's signed re-verification conditions for baseline or dependency changes and obtain re-review for semantic overlap or changed test hashes.
