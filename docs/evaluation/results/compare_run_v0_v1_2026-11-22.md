# V0 vs V1 — NVDA, 2026-11-22 (comparable run)

## Status

**Comparable: `scripts/compare_runs.py` exited 0.** Both runs use the same ticker,
trade date, asset type, models, provider, language, prompt hashes and
`evidence_mode: strict`. There is **one run per variant**, so the numbers below are
descriptive measurements of these two runs, not a stable estimate of each variant.

## Provenance

- Generated: 2026-11-25 19:14 +08:00, re-run against the archived manifests below.
- Command:

  ```bash
  .venv/bin/python scripts/compare_runs.py \
    docs/evaluation/results/manifests/v0-nvda-2026-11-22-r1-20261125t1054/manifest.json \
    docs/evaluation/results/manifests/v1-nvda-2026-11-22-r1-20261125t1059/manifest.json
  ```

- Manifests (archived copies used for this re-run):
  - v0: `docs/evaluation/results/manifests/v0-nvda-2026-11-22-r1-20261125t1054/manifest.json`
  - v1: `docs/evaluation/results/manifests/v1-nvda-2026-11-22-r1-20261125t1059/manifest.json`
- Originals remain under `outputs/runs/<same run ids>/`. Each archived directory is
  a verbatim copy of the whole run directory — `manifest.json`, `evidence-mode.json`,
  prompt receipts and the evidence snapshot — verified with `diff -r`.
- The sidecar matters: the tool reads `evidence-mode.json` from the manifest's parent
  directory. Both archived sidecars say `strict`, so the re-run kept
  `evidence_mode: strict` and reproduced the identical numbers and exit code 0.

## What actually differs between v0 and v1

| Config key | v0 | v1 |
| --- | --- | --- |
| `workflow_variant` | `v0` | `v1` |
| `max_debate_rounds` | 2 | 1 |
| `max_risk_discuss_rounds` | 1 | 1 |

Every other `config_snapshot` field is identical: both tiers use
`CS5351/DeepSeek-V4-Flash`, `llm_provider=openai_compatible`,
`output_language=English`, the same news/tool limits, `holding_period_days=5`,
and the same memory path. The `bull`, `bear` and `research_manager` prompt hashes
are identical in both manifests.

Per the v1 selector delivery record (`docs/approvals/gate1-C-v1-fixed-pruning.md`)
and the selector implementation in `src/tradingagents/graph/trading_graph.py`:
**v0 runs two Bull/Bear research debate rounds; v1 prunes this to one.** Risk
discussion depth (one round) and the three-role flow are unchanged. This is a
fixed structural reduction, not adaptive collaboration (v2).

## Measured results (tool output, exit 0)

| Metric | v0 | v1 | Δ v1 − v0 |
| --- | --- | --- | --- |
| outcome | Hold | Sell | changed (single observation) |
| LLM calls | 21 | 21 | 0 |
| tool calls | 22 | 29 | +7 (+31.8%) |
| tokens in | 155,861 | 154,080 | −1,781 (−1.1%) |
| tokens out | 33,661 | 28,492 | −5,169 (−15.4%) |
| tokens in + out | 189,522 | 182,572 | −6,950 (−3.7%) |
| duration (s) | 210.18 | 160.98 | −49.20 (−23.4%) |
| stop reason | completed | completed | — |
| failure | null | null | — |

Each variant has exactly one run, so its per-variant average equals that run.

## Reading the difference

- v1 used the **same number of LLM calls and the same prompts**, but made **more
  tool calls** while producing **fewer output tokens** and finishing about
  **23% faster**. The saving is concentrated in output tokens; input tokens
  barely moved (−1.1%).
- Total tokens fell only **3.7%**, well short of the team's 20–25% reduction
  target. This run does not demonstrate that target being met.
- The final decision changed from **Hold to Sell**. With one sample per variant
  this cannot be attributed to debate pruning with confidence. No quality or
  semantic score is computed here (owned by B/D).
- Both runs stopped with `completed`, had no failure, and carried real prompt
  hashes and real evidence-snapshot references. The table is not invented.

## Field status and caveats

- Real/measured: `usage`, `duration_seconds`, `outcome`, `stop_reason`, prompt
  hashes, evidence snapshot IDs, `evidence_mode: strict`.
- Not available here: semantic/quality scores, pass thresholds, run-to-run
  variance (no repeats per variant). Other evidence-sidecar decision fields
  (`policy_version`, `authoritative_action`, `decided_by`) are null in both runs.
- No V2 run exists yet. Do not generalize these deltas beyond this single
  NVDA / 2026-11-22 comparison.
