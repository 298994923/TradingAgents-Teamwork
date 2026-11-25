# V0 vs V1 — NVDA, 2026-11-24 (comparable run)

## Status

**Comparable: `scripts/compare_runs.py` exited 0.** Both runs record the same
ticker, trade date, asset type, models, provider, output language, three prompt
hashes and `evidence_mode: strict`. There is **one run per variant**, so the
numbers below are descriptive measurements of these two runs, not a stable
estimate of either variant.

## Provenance

- Generated: 2026-11-25 19:40 +08:00 from the original manifests under
  `outputs/runs/` (no archived copies were made for this comparison).
- Command:

  ```bash
  .venv/bin/python scripts/compare_runs.py \
    outputs/runs/v0-nvda-2026-11-24-r1-20261125t1121/manifest.json \
    outputs/runs/v1-nvda-2026-11-24-r1-20261125t1129/manifest.json --json
  ```

- Manifests:
  - v0: `outputs/runs/v0-nvda-2026-11-24-r1-20261125t1121/manifest.json`
  - v1: `outputs/runs/v1-nvda-2026-11-24-r1-20261125t1129/manifest.json`
- `created_at`: v0 `2026-11-25T11:24:32Z`, v1 `2026-11-25T11:31:50Z` (about
  seven minutes apart). Both sidecars report `evidence_mode: strict`.

## What actually differs between v0 and v1

| Config key | v0 | v1 |
| --- | --- | --- |
| `workflow_variant` | `v0` | `v1` |
| `max_debate_rounds` | 2 | 1 |
| `max_risk_discuss_rounds` | 1 | 1 |

Every other `config_snapshot` field is identical: both tiers use
`CS5351/DeepSeek-V4-Flash`, `llm_provider=openai_compatible`,
`output_language=English`, the same news/tool limits, `holding_period_days=5`
and the same memory path. All three prompt hashes are identical in both
manifests, so the comparison is not confounded by a prompt change.

Per the v1 selector implementation in
`src/tradingagents/graph/trading_graph.py`, v0 runs two Bull/Bear research
debate rounds and v1 prunes this to one; risk depth and the three-role flow are
unchanged. This is a fixed structural reduction, not adaptive collaboration
(v2). The manifest counts confirm it: 24 vs 21 LLM calls.

## Measured results (tool output, exit 0)

| Metric | v0 | v1 | Δ v1 − v0 |
| --- | --- | --- | --- |
| outcome | Hold | Hold | unchanged |
| LLM calls | 24 | 21 | −3 (−12.5%) |
| tool calls | 26 | 34 | +8 (+30.8%) |
| tokens in | 160,910 | 175,220 | +14,310 (+8.9%) |
| tokens out | 33,495 | 30,148 | −3,347 (−10.0%) |
| tokens in + out | 194,405 | 205,368 | +10,963 (+5.6%) |
| duration (s) | 209.51 | 160.28 | −49.23 (−23.5%) |
| stop reason | completed | completed | — |
| failure | null | null | — |

Each variant has exactly one run, so its per-variant average equals that run.

## Reading the difference

- v1 finished about **23% faster** with **three fewer LLM calls** and **10%
  fewer output tokens**, but made **eight more tool calls** and consumed **9%
  more input tokens**. Total tokens actually **rose 5.6%**, so this run does
  not demonstrate the team's 20–25% token-reduction target.
- The final outcome is **Hold in both runs** — identical here, unlike the
  2026-11-22 comparison where it changed. With one sample per variant, neither
  outcome agreement nor disagreement can be attributed to debate pruning with
  confidence. No quality or semantic score is computed here (owned by B/D).
- Both runs stopped with `completed`, had no failure, and carry real prompt
  hashes and real evidence-snapshot references. The table is not invented.

## Field status and caveats

- Real/measured: `usage`, `duration_seconds`, `outcome`, `stop_reason`,
  prompt hashes, evidence snapshot IDs, `evidence_mode: strict`.
- The two `evidence_snapshot` IDs differ (v0 `sha256:67d21aae…`, v1
  `sha256:d5f8a029…`); each run publishes its own artifact, so this is
  expected, not a discrepancy. `source_run_id` matches the respective run id.
- Not available here: semantic/quality scores, pass thresholds, run-to-run
  variance (no repeats per variant). Other evidence-sidecar decision fields
  (`policy_version`, `authoritative_action`, `decided_by`) are null in both
  runs.
- The runs were created about seven minutes apart on the same ticker and date;
  live data or tool responses could still differ. No V2 run exists. Do not
  generalize these deltas beyond this single NVDA / 2026-11-24 comparison.
