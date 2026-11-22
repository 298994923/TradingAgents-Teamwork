# Evaluation results (formal publication slot)

This directory is the **only** place for results the report may cite. Anything in
`results/B/` or `docs/plans/` is a draft, not a published result (see
`docs/handoffs/E-to-B-pilot-reply.md`).

## Files

- [`v0-nvda-2026-11-20.md`](v0-nvda-2026-11-20.md) — V0 baseline, three runs on a
  trading day with real market data. **Not a comparison**: `prompt_hashes` is empty,
  so `scripts/compare_runs.py` refuses it. No V1/V2 run exists yet.

## Rules

- A comparison is published only when inputs are comparable and the tool exits 0.
- Every file records commit, manifest paths, and which fields were real vs placeholder.
- Never backfill version anchors into historical/pilot records.
- Do not write a comparison table from data the tool refused.
