# RunEvent Contract

Owner: E (runtime records, experiments, CI, delivery).
Status: **step 1 — documentation only.** No `run_recorder.py` and no tests exist yet.
Consumers: `src/tradingagents/run_recorder.py` (planned), `scripts/compare_runs.py`
(planned), evaluation results (`docs/evaluation/results/`, planned).

This contract defines the on-disk JSON "run manifest" that records one analysis run
well enough to compare runs and to gate prompt/model changes. It is deliberately
minimal in this slice; fields owned by other members are marked and are **not**
validated here.

## Design rules

- **Deterministic by injection.** The recorder never reads the wall clock or a random
  source internally. `created_at`, `run_id`, and `version` are passed in explicitly;
  serialization uses `json.dumps(..., sort_keys=True, ensure_ascii=False, indent=2)`.
  Two calls with identical inputs produce identical bytes ("byte-stable manifest").
- **Run identity is structured, not random.** `run_id` is supplied by the caller and is
  never generated inside the recorder. Recommended shape
  `<variant>-<ticker>-<trade_date>-r<repeat>-<runstamp>`, e.g.
  `v2-nvda-2026-11-20-r1-20261121t1200`; it must match `^[a-z0-9][a-z0-9.-]{0,62}$`.
  The recorder refuses to overwrite an existing manifest file.
- **Schema is versioned.** Top-level `schema_version` is an `int`. The recorder writes
  `1` and rejects a manifest whose `schema_version` is not the supported value on read
  (explicit error, no silent coercion).
- **No secrets on disk.** Config keys whose name matches a secret pattern
  (`*_api_key`, `*_key`, `backend_url`, `*_token`, `*_password`) are excluded from
  `config_snapshot`; the manifest records only what is safe to compare.
- **Owned fields are not validated here.** `stop_reason` and the evidence/prompt
  snapshot shapes are contracts owned by C and A respectively. This slice stores them
  as opaque values and does **not** assert a value domain for them.

## Field list (schema_version 1)

| # | Field | Type | Req? | Inject./Caller-supplied | Owner | Notes |
|---|---|---|---|---|---|---|
| 1 | `schema_version` | `int` (== 1) | required | recorder | E | Read rejects any other value. |
| 2 | `run_id` | `str`, `^[a-z0-9][a-z0-9.-]{0,62}$` | required | caller | E | Unique within the results root; the recorder refuses to overwrite an existing file. Never generated internally. No `/`, no `..`, ≤ 64 chars. |
| 3 | `created_at` | `str` (ISO-8601) | required | caller | E | Not `datetime.now()` internally. |
| 4 | `version` | `str` | required | caller (`tradingagents.__version__`) | E | Package version that produced the run. |
| 5 | `ticker` | `str` (non-empty) | required | caller | E | `company_of_interest` for the run. |
| 6 | `trade_date` | `str` (`YYYY-MM-DD`) | required | caller | E | Analysis date. |
| 7 | `asset_type` | `str` | required | caller | E | e.g. `stock`, `crypto`. |
| 8 | `outcome` | `str` or `null` | required (may be null) | caller | E | Final rating string, or `null` if the run produced none. |
| 9 | `config_snapshot` | `object` (str→scalar) | required | caller | E | Run settings minus secret-pattern keys (rule above). |
| 10 | `prompt_hashes` | `object` (str→str) | required (may be `{}`) | caller | B | Prompt name → hash. Shape/owner: B. Not validated here. |
| 11 | `evidence_snapshot` | `object` or `null` | required (may be null) | caller | A | Evidence snapshot id/pointer. Shape/owner: A. Not validated here. |
| 12 | `usage` | `object` | required | caller | E | `{llm_calls:int, tool_calls:int, tokens_in:int, tokens_out:int}`. |
| 13 | `duration_seconds` | `number` (>= 0) or `null` | required (may be null) | caller | E | Wall time measured by the caller, passed in. |
| 14 | `failure` | `str` or `null` | required (may be null) | caller | E | Failure summary if the run failed. |
| 15 | `stop_reason` | `str` or `null` | required (may be null) | caller | **C** | Opaque here. Value domain owned by C's `execution_policy`; **not validated in this slice.** |

All 15 keys are present on every manifest (nullable ones set to `null`). Required
`str` fields reject empty strings. Missing required keys, or an unsupported
`schema_version`, are rejected on write and on read.

## Run identity (`run_id`)

Format is recommended, not enforced by the recorder; the recorder validates only the
charset and the no-overwrite rule.

| Segment | Example | Meaning |
|---|---|---|
| `variant` | `v2` | Architecture variant: `v0` original, `v1` trimmed, `v2` adaptive |
| `ticker` | `nvda` | Lower-case symbol |
| `trade_date` | `2026-11-20` | Analysis date — **not** the date the run happened |
| `r<repeat>` | `r1` | 1-based repetition index for identical inputs |
| `runstamp` | `20261121t1200` | Run time, UTC, `YYYYMMDDtHHMM` |

Rules:

- Charset `^[a-z0-9][a-z0-9.-]{0,62}$` — lower case only, no `/`, no `..`, ≤ 64 chars.
  This is what makes the id safe to use as a directory name under the results root.
- Uniqueness is enforced by the recorder: `write_manifest` raises if the target file
  already exists and never overwrites.
- `build_run_id(variant, ticker, trade_date, repeat, at)` is a pure helper that formats
  the id. `at` is a parameter, so the recorder still never reads the clock.

Why both the repeat index and the runstamp exist: the repeat index is a *design*
dimension (repeated runs of identical inputs, e.g. three samples for variance), while
the runstamp is the *physical* fact of when the run happened. Two runs of the same
variant/ticker/date after a code change differ only by `runstamp`; without it they
would collide and one result would be silently lost.

## What this contract deliberately does not define

- No `stop_reason` enum (C owns it — see C §6.5 and `execution_policy.py`, planned).
- No prompt-hash algorithm (B owns prompt versioning, `prompts/prompt_v1.x.yaml`).
- No evidence snapshot schema (A owns `evidence.py` and `evidence.md`).
- No CLI/graph/stats integration (later steps depend on C's `AgentState` and stop enum).
- No CI gate. Gates (§6) are a later E step.

## Negative cases the future recorder test must cover (slice 2)

- Missing required field (e.g. `version`) → rejected with a specific error.
- Unsupported `schema_version` → rejected with a specific error.
- Secret-pattern config key (e.g. `openai_api_key`) → absent from `config_snapshot`.
