# B contribution to the shared trace matrix

Scope: B coursework evidence, with separately identified team-main checks at 58f8ee5. Monitor columns describe what to observe. Production monitoring coverage requires integration verification.

| ID | Enforcing component in B design | Runtime observation | Historical coursework test name | Historical evidence and limits | Team main check |
|---|---|---|---|---|---|
| B-REQ-01 | opening-input filter | Opponent fingerprint hits per opening | test_researcher_actual_prompts; test_blind_round_and_reverse_control | S7 capture; S9 opening leakage 0/3 | Direct coverage unverified |
| B-REQ-02 | targeted response validator | Off-target or unlinked accepted replies | test_researcher_actual_prompts; test_claim_validation | S9 target hits 6/6 | Direct coverage unverified |
| B-REQ-03 | claim batch validator | Invalid accepted batches | test_claim_validation | Offline mutation cases | Direct coverage unverified |
| B-REQ-04 | citation checker | Accepted invalid or future references | test_claim_validation | S9 valid evidence IDs 30/30; strict snapshot binding needs A/C | Direct coverage unverified |
| B-REQ-05 | repair wrapper | Repair attempts per output | test_repair_once | Offline repair paths; live repair no_sample | Direct coverage unverified |
| B-REQ-06 | context builder | Layer-order violations | test_budget_boundary_and_compaction | Offline layer construction | Direct coverage unverified |
| B-REQ-07 | context builder | Mandatory overflow and dropped blocks | test_budget_boundary_and_compaction; test_impossible_budget | Offline budget boundaries | test_b_context_wiring.py: mandatory overflow before call or receipt |
| B-REQ-08 | context builder | Protected constraint ID and text retention | test_budget_boundary_and_compaction; test_impossible_budget | S9 compacted packs 3/3 retained constraints | Direct coverage unverified |
| B-REQ-09 | context deduplication | Exact-text and metadata duplicates; priority distinctions retained | test_context_dedup; test_fingerprint | Offline fingerprint cases | test_context_builder.py: history priority after deduplication (partial) |
| B-REQ-10 | research manager | Unaccounted unresolved pairs | test_manager_decision | S9 unresolved pairs retained 3/3; graph handoff pending | test_b_context_wiring.py: latest arguments retained (partial) |
| B-REQ-11 | legacy replay harness | Prompt and state differences | test_matched_protocol | S7 archived matched replay and legacy equivalence evidence | Direct coverage unverified |
| B-REQ-12 | usage measurement | Missing source or unsupported granularity | test_metrics_and_placement | S9 estimated inputs 9/12; manager estimates unavailable | Direct coverage unverified |

On 2026-11-20 the fixed coursework S9 run reported 6/6 targeted replies. On 2026-11-24 the offline replay used simulated responses: v1.0 and v1.1 each recorded target hits 0/6 and structural validity 0/12. Each version verified 12/12 input receipts. Both functional criteria failed in that replay. Relative live-model quality remains unmeasured.

Main selectors and scope:

- test/offline/test_b_context_wiring.py::test_researcher_compacts_history_and_receipts_match_sent_input
- test/offline/test_b_context_wiring.py::test_manager_keeps_latest_arguments_from_both_sides
- test/offline/test_b_context_wiring.py::test_required_context_over_budget_stops_before_call_or_receipt
- test/offline/test_context_builder.py::test_history_priority_survives_deduplication

These cover compacted input and its hash, latest manager arguments, before-send failure, and priority-sensitive deduplication. Blind openings, assigned targets, typed manager deltas and whole-graph budget admission require separate evidence.

- test_blind_round_and_reverse_control — historical selector; definition absent from team main 58f8ee5
- test_budget_boundary_and_compaction — historical selector; definition absent from team main 58f8ee5
- test_claim_validation — historical selector; definition absent from team main 58f8ee5
- test_context_dedup — historical selector; definition absent from team main 58f8ee5
- test_fingerprint — historical selector; definition absent from team main 58f8ee5
- test_impossible_budget — historical selector; definition absent from team main 58f8ee5
- test_manager_decision — historical selector; definition absent from team main 58f8ee5
- test_matched_protocol — historical selector; definition absent from team main 58f8ee5
- test_metrics_and_placement — historical selector; definition absent from team main 58f8ee5
- test_repair_once — historical selector; definition absent from team main 58f8ee5
- test_researcher_actual_prompts — historical selector; definition absent from team main 58f8ee5
