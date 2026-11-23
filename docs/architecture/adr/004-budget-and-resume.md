# 004-budget-and-resume.md

**C local draft v0.1 · Proposed, not adopted · 2026-11-23**

## Context and scope

`C-keyed-checkpoint-graph-review-package.md` v0.1 proposes a programmatic checkpoint lifecycle change only. At `integration@a61b7b587169bcfb20300be1b95f721e1a496caa`, unkeyed runs with the same ticker, date, and compatibility signature share a thread. A caller needs to distinguish otherwise identical runs without invalidating existing checkpoints or changing what makes a run compatible.

The integration ADR inventory has ADR-003 for review/context and ADR-005 for the deterministic guard. Neither governs this change; the budget/resume ADR and execution-budget contract named in `AGENTS.md` are absent from that commit. This draft supplies a decision for review, not authorization to edit a protected file. The accompanying `execution-budget.md` records the separate budget contract; the keyed lifecycle changes no budget behavior.

## Proposed decision

1. Add optional keyword-only `run_key: str = ""` to `TradingAgentsGraph.propagate()` and carry it per call through `checkpoint_scope()`, `begin_checkpoint()`, `_run_graph()`, and `clear_checkpoint_on_success()`. Use the same key with the existing C storage helpers for thread ID, saved-step lookup, and cleanup. Inject that exact thread ID into invocation config. If that thread has a resumable step, resume with `None` and execute only pending work; if there is no resumable step, use the existing programmatic fresh-run behavior for the requested thread, without falling back to a sibling or legacy thread.
2. Keep `_run_signature()` and its compatibility inputs unchanged. `run_key` selects a run within the same compatibility namespace; it does not relax compatibility or replace the signature. Omitted and empty keys preserve the exact legacy ID and behavior. Nonempty keys use the storage candidate's versioned, structured encoding of ticker, date, signature, and key, without changing the per-ticker SQLite location. Callers choose distinct keys for distinct runs and repeat the original key to resume.
3. Keep the disabled-checkpoint early return before SQLite access, with or without a key. On normal programmatic success, keep the existing cleanup order and use the same ticker, date, signature, and key to remove only that thread's rows in `checkpoints` and `writes`. Preserve sibling keyed and legacy rows. This is derived-key cleanup, not the separate locator-based exact-thread cleanup API or a new manifest-publication guarantee.
4. Do not alter the constructor or its `on_prompt` forwarding. Preserve B's actual Bull, Bear, and Research Manager receipts and the legacy report path. The receipt control verifies digests of the prompts the model saw; it does not establish a pre-invocation prompt-compatibility fingerprint.

Only `src/tradingagents/graph/trading_graph.py` is proposed for production edits. The C storage candidate at `e611e0daefa91257a1fd01d7410afc2f45160901` is a prerequisite already exercised in the disposable checkout, not part of the graph edit. V1 selection, CLI, Evidence binding, locator recovery, manifest publication, budget admission and routing are out of scope.

## Verification and acceptance

| Decision | Review test | Actual integration baseline |
| --- | --- | --- |
| A keyed interruption resumes only pending work; success clears that thread and leaves sibling and legacy rows | `test_checkpoint_graph_run_key.py` — `test_keyed_propagate_resumes_and_cleans_up_only_its_thread` | Expected failure: `propagate()` rejects `run_key` before exercising the lifecycle. |
| Omission still resumes and clears the legacy thread; disabled mode does not open SQLite | `test_checkpoint_graph_run_key.py` — `test_omitted_key_resumes_and_cleans_up_legacy_thread`, `test_disabled_checkpointing_does_not_open_sqlite` | Omitted legacy and disabled controls passed; disabled keyed case failed at the same keyword boundary. Explicit empty-key identity is covered by the storage candidate's `test_checkpoint_thread_identity.py`. |
| Legacy route and reports still complete and actual prompt receipts remain intact | `test_checkpoint_graph_prompt_receipts.py` — `test_unkeyed_checkpoint_route_preserves_real_prompt_receipts` | Passed: Bull, Bear, and Research Manager receipts arrived in order and their digests matched the scripted model inputs. |

The exact SHA-256 values are `cffd4df67fc834d9d7a6d3f43705ebaeb84b10e263cd0d24d2291ea39a26d713` for `test_checkpoint_graph_run_key.py` and `d86e8277d8c640014295244c1d2cbf5b6a656e2e782ab204578c972dc933b643` for `test_checkpoint_graph_prompt_receipts.py`. The review run recorded **2 expected failures and 16 passing controls**, including 13 legacy cases in `test_checkpoint_lifecycle.py` and `test_checkpoint_resume.py`. The separate storage/legacy run recorded **36 passing tests**. After authorization, rerun both review files, the storage tests, and the legacy regressions, plus Ruff and `git diff --check`. Keyed graph acceptance is pending. `REQ-C-LOCAL-CKPT-004` and `INV-C-LOCAL-CKPT-004` are provisional local references.

## Existing decisions and approval boundary

`D-to-C-review-checkpoint-compat.md` distinguishes legacy automatic continuation from explicit adaptive recovery: an incompatible explicit recovery must make the mismatch visible, invoke zero nodes, and preserve the old checkpoint. `E-to-C-evidence-checkpoint-response (2).md` §8 and `C-evidence-checkpoint-recovery-plan.md` separately track locating the original run, Evidence verification, and preserving the checkpoint until successful terminal publication. This proposal neither implements nor changes those rules. ADR-005, `005-deterministic-guard.md`, still governs the guard and is not authorization for this graph edit.

Independent approval of review package v0.1, the two exact test versions, and the protected modification scope is still required, along with adoption of a covering ADR and explicit human authorization for `trading_graph.py`. This draft records none of those approvals.
