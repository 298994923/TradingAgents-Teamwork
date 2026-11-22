# Evaluation Protocol

Owner: E (runtime records, experiments, CI, delivery). Reviewers: B (collaboration /
prompt versioning) and D (deterministic safety) per the team split §3.
Status: **tooling only.** `scripts/compare_runs.py` and `test/offline/test_compare_runs.py`
exist and pass offline; **no experiments have run yet**. The comparison tables the
report needs (`docs/evaluation/results/`) do not exist and must not be fabricated.

This protocol fixes *how* runs are compared and *what* a comparison may claim. It
does not define semantic-quality scoring: that spec is owned by B and D and is not
implemented in this slice (see "Out of scope" below). Until real runs exist, this
document and the tool are the only deliverables here.

## Fixed inputs (the comparison set)

Two runs may be compared only when these inputs are identical to the baseline. The
tool enforces this; a mismatch is refused, not averaged or shown side by side.

| Guard key | Source | Why it must match |
|---|---|---|
| `ticker` | manifest top level | different company = different question |
| `trade_date` | manifest top level | different analysis date = different information set |
| `asset_type` | manifest top level | `stock` vs `crypto` changes tools and rules |
| model | `config_snapshot.quick_think_llm`, `deep_think_llm` | a model change is the very thing being evaluated |
| provider | `config_snapshot.llm_provider` (+ optional `*_think_provider`) | different backend = different outputs |
| language | `config_snapshot.output_language` | report text changes with language |
| prompt | `prompt_hashes` (name → hash) | a prompt change invalidates a like-for-like comparison |

A missing required config key (model, provider, language) is treated as
**incomparable** — the tool refuses rather than guessing a default.

## Variants

Each run is tagged by the first segment of its `run_id`
(`<variant>-<ticker>-<trade_date>-r<repeat>-<runstamp>`):

| Variant | Meaning |
|---|---|
| `v0` | original upstream path (baseline for comparison) |
| `v1` | trimmed / simple reduction |
| `v2` | adaptive collaboration |

Comparing a run against itself-other-variants is the point; comparing different
inputs is refused.

## Metrics reported

Only quantities the manifest actually records. Per run: `outcome`, `usage`
(`llm_calls`, `tool_calls`, `tokens_in`, `tokens_out`), `duration_seconds`,
`failure`, `stop_reason`. Per variant: **count of runs** and the **average** of each
numeric field (`null` values excluded from that field's average).

The token-reduction goal from the team plan (e.g. 20–25%) is a *target*, not a
result: the protocol reports measured averages; it does not assert the target was
met. If real runs do not hit it, the results file says so.

## Thresholds

Thresholds for a *passing* comparison are intentionally left unset here. They belong
with the semantic-evaluation spec (B/D) and the CI semantic gate (§6.4). This slice
ships no threshold and no gate; it only produces comparable numbers.

## Out of scope (owned elsewhere)

- **Semantic / quality scores** (faithfulness, relevance, argument independence): B
  and D. This tool does not compute, infer, or approximate them. The absence of a
  score is the honest output.
- **`stop_reason` value domain**: C (`execution_policy`). Reported opaquely.
- **Evidence snapshot semantics**: A (`evidence.py`). Reported opaquely.
- **Live evaluation runs**: `test/live/test_fixed_eval.py` (later; needs API access).

## How to run

```bash
# Compare two or more manifests of the same input across variants.
python scripts/compare_runs.py results/v0-nvda-.../manifest.json \
                             results/v2-nvda-.../manifest.json
python scripts/compare_runs.py ... --json     # machine-readable output

# Offline tests (no network, no API keys).
pytest test/offline/test_compare_runs.py -q
```

Exit codes: `0` comparable, `1` refused (reason on stderr names the differing guard
key), `2` usage error. Results meant for the report go under
`docs/evaluation/results/`, one file per comparison, with the commit and manifest
paths recorded — **only after the runs actually happen**.

## Current state

- Comparison tooling: implemented, 20 offline tests green.
- Experiments: **none run.** No `results/` files exist. Do not add comparison tables
  until real manifests are produced from real runs.
