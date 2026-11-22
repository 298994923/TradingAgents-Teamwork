# Package B tests-first specification

FuKaichao (60468706). The owner approved S1 with the message `approve S1` on 2026-11-20. S2 approval is pending. PR description when submitted: tests first, no implementation yet.

## Cases

| Case ID or pytest name | Requirement / invariant | Polarity | Observable expectation |
|---|---|---|---|
| missing | B-REQ-03 / INV-B2 | Negative | Missing speaker yields MISSING_FIELD |
| duplicate | B-REQ-03 / INV-B2 | Negative | Repeated claim ID yields DUP_ID |
| blank | B-REQ-03 / INV-B2 | Negative | Whitespace-only text yields EMPTY_STATEMENT |
| long | B-REQ-03 / INV-B2 | Negative | 81 characters against an injected cap of 80 yields TOO_LONG |
| unknown-target, self-target | B-REQ-03 / INV-B2 | Negative | Both yield BAD_RESPONDS_TO |
| future-target | B-REQ-03 / INV-B2 | Negative | A known later-round claim yields FUTURE_REF |
| empty-evidence, malformed-evidence, missing-evidence, undated-evidence, future-evidence | B-REQ-04 / INV-B3 | Negative | INVALID_EVIDENCE plus distinct detail codes EMPTY, MALFORMED, MISSING, UNKNOWN_TIME, FUTURE |
| valid | B-REQ-03/04 / INV-B2/B3 | Positive | The earlier opponent claim and valid evidence are accepted |
| test_repair_once[False] | B-REQ-05 / INV-B5 | Negative | One failed repair, explicit degradation and reason, hashed raw artifact in the run directory |
| test_repair_once[True] | B-REQ-05 / INV-B5 | Positive | One successful injected format repair |
| test_fingerprint | B-REQ-09 | Both | Full-width/case/spacing/punctuation variants match the expected digest; different wording remains distinct |
| test_blind_round_and_reverse_control | B-REQ-01 / INV-B1 | Both | Exercise both speaker assignments. Clean generated input passes; deliberately contaminated input raises |
| test_impossible_budget | B-REQ-07/08 / INV-B4 | Negative | One-token budget raises ContextBudgetError |
| test_budget_boundary_and_compaction | B-REQ-06/07/08 / INV-B4/B6 | Both | Exact limit preserves order; one token over triggers compaction; retain both exact constraint fingerprints and log dropped items |
| test_context_dedup | B-REQ-09 | Both | Keep first eligible duplicate and lexically distinct evidence; record duplicate_of |
| test_metrics_and_placement | B-REQ-12 | Both | Absent usage remains unknown; injected usage yields signed error; snapshot and result use separate temporary subtrees |

## Proposed test interfaces

Tests import the actual B modules inside each test so the full suite collects before implementation. The only doubles are the evidence oracle, repair callable, character-count estimator and supplied usage data. Fit thresholds and functional signatures are proposals for approval. Evidence details preserve the fixed top-level error vocabulary. Estimation error is estimated input tokens minus actual input tokens. The budget fixture sets a 100% trigger to isolate the exact boundary; production defaults remain open. This fixture makes L4 disposable and supplies L5 explicitly. Integration checks at S4/S6 must also intercept actual researcher and manager invocations; this blind assembly test alone does not prove graph wiring.

## Reproduction and status

From the working repository root, using the isolated Python environment established in S0:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q test/offline/test_review.py test/offline/test_context_builder.py
```

Initial run (2026-11-20), tested before implementation:

```text
E       ModuleNotFoundError: No module named 'tradingagents.review'
E       ModuleNotFoundError: No module named 'tradingagents.context_builder'
21 failed in 0.64s
```

The 13 JSON fixtures expand to 13 validation tests. Three additional review tests and five context tests bring the collected total to 21. All failures occur at the first import of the relevant unimplemented module. No skips, live calls or passing behavioral claims. Application output tests change into pytest's temporary directory; bytecode and pytest cache creation are disabled in the reproduction command.
