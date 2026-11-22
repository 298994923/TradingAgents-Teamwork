# S9 fixed-set evaluation

Model: CS5351/DeepSeek-V4-Flash. Three fresh repetitions per case. Temperature 0; seed unspecified. Record-level provenance and hashes are in the companion JSON.

| Metric | Samples | Passes | Rate | Repeat mean | Range width | Threshold | Met |
|---|---:|---:|---:|---:|---:|---:|---|
| first_round_leakage | 3 | 3 | 0 | 0 | 0 | 0 | True |
| target_hit | 6 | 6 | 1 | 1 | 0 | 1 | True |
| valid_evidence | 30 | 30 | 1 | 1 | 0 | 1 | True |
| constraint_retention | 3 | 3 | 1 | 1 | 0 | 1 | True |
| disagreement_retention | 3 | 3 | 1 | 1 | 0 | 1 | True |
| structural_validity | 12 | 12 | 1 | 1 | 0 | 1 | True |
| repair_success | 0 | 0 | not_run | not_run | not_run | 1 | not_run |

Rates count leaks per captured opening, exact assigned links per targeted response, valid IDs per parseable raw citation, retained L1 text per compacted pack, retained pairs per manager output (including fallback), accepted final structures per response, and successful repairs per attempted repair. Spread is max minus min across available repetition rates. Zero attempts produce no repair score.

| Case / repeat | Actual input (metrics.json) | Estimated input | Error (estimate - actual) | Actual output | Elapsed seconds |
|---|---:|---:|---:|---:|---:|
| blind / 1 | 295 | 278 | -17 | 319 | 8.907 |
| target-full / 1 | 460 | 413 | -47 | 178 | 8.896 |
| target-compact / 1 | 374 | 343 | -31 | 490 | 7.96 |
| manager / 1 | 320 | not_run | not_run | 106 | 1.14 |
| blind / 2 | 295 | 278 | -17 | 324 | 3.558 |
| target-full / 2 | 460 | 413 | -47 | 178 | 0.667 |
| target-compact / 2 | 374 | 343 | -31 | 140 | 2.543 |
| manager / 2 | 320 | not_run | not_run | 167 | 1.666 |
| blind / 3 | 295 | 278 | -17 | 319 | 0.193 |
| target-full / 3 | 460 | 413 | -47 | 167 | 1.921 |
| target-compact / 3 | 374 | 343 | -31 | 490 | 0.181 |
| manager / 3 | 320 | not_run | not_run | 106 | 0.266 |

Matched compact-minus-full input-token deltas: [-86, -86, -86]. Observed estimator error band: (-47, -17).
Fabricated references: 0; malformed references: 0 (parseable outputs only).

A manifest covers one isolated model call, timed around the provider request, not a production graph round. The team manifest writer ran in each isolated trial directory. Manager prompts bypass the B context estimator.

The S8 team snapshot contains no docs/evaluation/protocol.md. These results follow the B brief and await E's protocol reconciliation. Target hits measure accepted links, not the persuasiveness of an argument. Thresholds apply only to this fixed set.

Prompt v1.1: insufficient evidence for adopting a new version; no candidate v1.1 was compared. Inspect failures and test a candidate on the same inputs before changing versions.

Reproduce from the checkout root: `PYTHONPATH=. python test/live/test_review_quality.py --reporting /path/to/team/src/tradingagents/reporting.py`
