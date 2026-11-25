# TradingAgents-Teamwork

CS5351 *Agentic Software Engineering* team project: a LangGraph multi-agent
trading-research application, built on the open-source
[TradingAgents](https://github.com/TauricResearch/TradingAgents) baseline and
extended under an auditable AI-coding workflow.

> This is a research and software-engineering exercise, **not** a trading
> strategy and **not** investment advice. The upstream project does not claim
> reproducible returns, and neither do we. The application does not place live
> orders.

## Status

The upstream baseline is green and the team's extension modules, governance
documents and CI gates are in place. The table below reflects the current
repository; the section [CI and blocking gates](#ci-and-blocking-gates) states
exactly what each gate does and where its limits are.

| Item | Current value |
|---|---|
| Python | 3.12 (baseline measured on 3.12.16) |
| Upstream baseline | `TauricResearch/TradingAgents@9fa1196` |
| Migration to `src/` | commit `b5d2f67` |
| License | Apache License 2.0 (see `LICENSE`) |
| Full offline suite | `2014 passed, 2 skipped, 1 deselected, 100 subtests passed` (2026-11-25) |
| Lint | `ruff check src tests test scripts` clean |
| CI jobs | `tests`, `lint`, `semantic-eval`, `schema`, `test-approval`, `ai-use-log` |
| Requirements registry | 58 entries across all five roles (A, B, C, D, E) |
| Branch protection on `main` | required CI checks and approval from another person (verified on GitHub) |

## What the application does

A CLI run takes a ticker and an analysis date and drives a multi-agent research
pipeline:

```text
analysts (market / social / news / fundamentals)
        -> bull and bear researchers
        -> research manager
        -> trader
        -> risk debate (aggressive / neutral / conservative)
        -> portfolio manager
        -> final rating + reports + memory
```

The graph is implemented with LangGraph and is checkpointable, so a run can be
resumed. Analyst tools and market data go through the data-layer router; two
model tiers are supported (`quick` for analysts/researchers/trader, `deep` for
managers). Results are written as Markdown/HTML reports under the configured
results directory, and a longer-term memory log records decisions.

A completed run also writes a versioned JSON manifest that records its inputs,
configuration, prompt hashes, usage, duration, failure and stop reason. These
manifests are what make runs comparable and prompt/model changes reviewable.

## Upstream baseline and team additions

The repository imports the upstream project at commit `9fa1196` and moves the
packages into a `src/` layout without rewriting their behaviour. The migration
commit is `b5d2f67`; the frozen test baseline is recorded in
[`docs/evaluation/baseline.md`](docs/evaluation/baseline.md).

The team work is organised by role:

| Role | Responsibility |
|---|---|
| A | Evidence: requirement registry, evidence records and time validity |
| B | Collaboration: independent claims, targeted responses, layered context |
| C | Workflow: scheduling, execution budget, bounded loops, resume |
| D | Deterministic safety: hard invariants, final validation, permissions |
| E | Run records, experiments, CI blocking gates, delivery |

The team's additions extend the upstream project; they do not replace the
upstream regression suite.

## Architecture

The main entry point is `TradingAgentsGraph` in
[`src/tradingagents/graph/trading_graph.py`](src/tradingagents/graph/trading_graph.py).
It wires graph setup, propagation, conditional routing, checkpointing and the
agents. The CLI in [`src/cli/`](src/cli) owns interactive selection, display and
the run loop; `src/cli/stats_handler.py` tracks LLM/tool calls and token usage.

The master constraint document is
[`architecture-blueprint.md`](architecture-blueprint.md). Supporting artifacts
live under [`docs/architecture/`](docs/architecture/) (invariants, trace matrix,
permission model, runtime policy catalog, candidate evaluation table and ADRs
003–006) and [`docs/code-governance/`](docs/code-governance/) (structural and
verification constraints, MCP tool manifest). Interface contracts are under
[`docs/contracts/`](docs/contracts/).

Cross-cutting boundaries:

- **Data layer.** Only `src/tradingagents/dataflows/` may import vendor SDKs
  (Yahoo, Alpha Vantage, FRED, SEC EDGAR, Polymarket, Reddit, Stocktwits).
  `router.py` dispatches by category and configured vendor chain. Failures are
  raised as `VendorError` subclasses, never fabricated values. Invariant
  `INV-001` is enforced by `tests/test_layering.py`.
- **LLM clients.** All clients are created through
  `src/tradingagents/llm_clients/factory.py`; heavy provider SDKs are imported
  lazily so test collection needs no API key.
- **Authority boundary.** LLM output is advisory. Deterministic checks and the
  final validation layer are authoritative; a model must not be able to turn a
  blocked result into a pass. A non-executable guard verdict is also masked out
  of the Markdown and HTML reports by
  [`src/tradingagents/reporting.py`](src/tradingagents/reporting.py) and
  [`src/tradingagents/report_html.py`](src/tradingagents/report_html.py).
- **Run records.** [`src/tradingagents/run_recorder.py`](src/tradingagents/run_recorder.py)
  serialises a run manifest with a versioned 15-field schema. The recorder is
  deterministic, refuses to overwrite, excludes secret-shaped config keys and
  writes atomically; the read path rejects missing fields and unsupported schema
  versions. The contract is
  [`docs/contracts/run-event.md`](docs/contracts/run-event.md).
- **Usage accounting.** Each admitted model call settles once. Incomplete or
  late usage stays `null` rather than becoming zero, so an unaffordable call
  cannot look free. The budget contract is
  [`docs/contracts/execution-budget.md`](docs/contracts/execution-budget.md).
- **Context and memory.** The upstream memory log is retained. The team's
  layered context builder, compaction threshold and constraint re-injection are
  covered by [`docs/contracts/review-context.md`](docs/contracts/review-context.md)
  and ADR-003.

## Repository layout

```text
TradingAgents-Coursework/
├── README.md                       this file
├── AGENTS.md                       coding-agent entry point and code map
├── Prompt.md                       static startup prompt (D9)
├── architecture-blueprint.md       master architecture constraint document
├── Report.md                       team process report and reflections
├── pyproject.toml                  src layout, entry point, pytest/ruff config
├── opencode.jsonc                  enforced tool configuration
├── Dockerfile / docker-compose.yml
├── .agent/rules.md                 project covenant
├── .github/workflows/ci.yml        six CI gate jobs
├── docs/
│   ├── ai-use-log.yaml             per-PR AI-use log
│   ├── approvals.yaml              test-approval records
│   ├── req/                        requirements registry and schema
│   ├── architecture/               invariants, trace matrix, catalog, ADRs
│   ├── code-governance/            structural and verification constraints
│   ├── contracts/                  interface contracts
│   ├── evaluation/                 baseline, protocol and comparison results
│   └── evidence/                   evidence records and snapshots
├── prompts/                        versioned runtime prompt catalog
├── src/
│   ├── cli/                        Typer CLI, display and usage tracking
│   └── tradingagents/              graph, agents, dataflows, llm_clients, memory
├── test/
│   ├── offline/                    deterministic tests (38 files)
│   ├── live/                       API-dependent tests (reserved)
│   └── fixtures/                   test fixtures
├── tests/                          upstream regression suite
├── scripts/                        CI gate and comparison scripts
└── transcripts/                    annotated agent-session transcripts
```

## Setup

```bash
git clone https://github.com/298994923/TradingAgents-Teamwork.git
cd TradingAgents-Teamwork
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # fill in provider keys; never commit .env
```

The Bedrock extra is optional: `pip install -e ".[dev,bedrock]"`.

Run the CLI with `tradingagents` (installed console script) or
`python -m cli.main`. A scripted stub is available as `python main.py`.

## Tests

All commands run from the repository root after installing the package.

```bash
# Full offline suite: upstream tests/ + new test/offline/
python -m pytest -q

# New deterministic tests only
python -m pytest test/offline -q

# Upstream regression suite only
python -m pytest tests -q

# API-dependent tests (test/live/ is reserved; keys required)
python -m pytest test/live -m integration -q

# Static checks
ruff check src tests test scripts
```

Latest local full-suite result (2026-11-25): `2014 passed, 2 skipped,
1 deselected`, plus `100 subtests passed`. The skips are optional
`langchain_aws` and the real-model semantic case without an API key.
`test/live/` has no test cases yet, so there is **no** live-test pass to report;
a suite that was not run is not a suite that passed.

## CI and blocking gates

CI runs on every pull request and on pushes to `main`
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)). The workflow has six
jobs. Two of them only make sense for a PR and skip on a plain push.

Here is what each gate actually does today, in plain words:

- **`tests`** (Gate 5, regression) — runs the upstream `tests/` and our
  `test/offline/`. If a test fails, the PR is blocked. It does not count tests
  or compare against an old number.
- **`lint`** (Gate 2, static analysis) — runs ruff, compiles the code to catch
  syntax errors, and checks that every third-party import used by our source is
  declared in `pyproject.toml`. A few packages that upstream pulls in
  transitively are allowlisted.
- **`schema`** (Gate 3) — checks `docs/req/requirements.yaml` against
  `docs/req/req-schema.json`. The registry currently holds 58 entries from all
  five roles.
- **`test-approval`** (Gate 1) — if a PR changes a file under `src/`, that file
  must be listed in `docs/approvals.yaml` with an approver and a date. No
  matching record, no merge. This gate deliberately covers source code files.
- **`semantic-eval`** (Gate 4) — scores the rendered research prompts against a
  fixed evaluation set and includes a real-model judge case that skips without
  an API key. It writes results to the CI summary and is advisory
  (`continue-on-error`): it reports, but does not block a merge.
- **`ai-use-log`** (Gate 6) — if a PR changes `src/`, `scripts/` or `test/`, it
  must add a new entry to `docs/ai-use-log.yaml` with a fresh unique id and
  `human_reviewed: true`. Editing only docs, prompts or `.github/` does not
  trigger it.

To be honest about the state: `tests`, `lint` and `ai-use-log` are enforcing
gates that will block a bad PR. `test-approval` deliberately covers only `src/`,
the schema gate validates the registry but does not judge requirement quality,
and the semantic gate is advisory.

Branch protection on `main` is enabled and verified on GitHub: a pull request
needs passing CI checks and approval from another person before it can merge.
The author cannot approve their own change.

## Baseline, experiments and reproducibility

- Upstream: `TauricResearch/TradingAgents@9fa1196`, Apache-2.0.
- Migration to `src/`: commit `b5d2f67`.
- Frozen V0 test baseline: commit `b5d2f67`, Python 3.12.16, `1412 passed,
  1 skipped, 1 deselected`.
- Current additions extend the upstream suite; they do not replace it.

The exact commands and environment for the V0 baseline are in
[`docs/evaluation/baseline.md`](docs/evaluation/baseline.md) and
[`docs/evaluation/env.txt`](docs/evaluation/env.txt). The comparison method,
its fixed inputs and its limits are in
[`docs/evaluation/protocol.md`](docs/evaluation/protocol.md).

Runs are recorded as manifests (version, input, config, prompt hashes, usage,
duration, failure, stop reason), so comparisons are tied to a version rather
than to a screenshot. Two comparable V0/V1 results are published under
[`docs/evaluation/results/`](docs/evaluation/results/):

| Experiment | LLM calls (v0 → v1) | Output tokens (v0 → v1) | Duration (v0 → v1) |
|---|---|---|---|
| [2026-11-22](docs/evaluation/results/compare_run_v0_v1_2026-11-22.md) | 21 → 21 | 33,661 → 28,492 | 210.18 s → 160.98 s |
| [2026-11-24](docs/evaluation/results/compare_run_v0_v1_2026-11-24.md) | 24 → 21 | 33,495 → 30,148 | 209.51 s → 160.28 s |

Both comparisons were produced by `scripts/compare_runs.py` with exit code 0,
real prompt hashes and `evidence_mode: strict`. Each variant has one run, so
these are descriptive measurements, not a stable estimate. Total tokens fell
3.7% in the first experiment and rose 5.6% in the second; the team's 20–25%
reduction target is **not** demonstrated by these runs.

## Records and governance

Read, in order: [`AGENTS.md`](AGENTS.md) → [`Prompt.md`](Prompt.md) →
[`.agent/rules.md`](.agent/rules.md). The workflow requires human approval
before implementation, small reviewed changes with tests first, and a real
AI-use log entry for every code or prompt change. Every feature has at least one
negative test. Changes to safety-critical paths require an architecture
decision and human approval. Do not weaken or delete tests to make CI pass.

The audit records are [`docs/ai-use-log.yaml`](docs/ai-use-log.yaml),
[`docs/approvals.yaml`](docs/approvals.yaml) and
[`docs/approvals/`](docs/approvals/), with review and defect records in
[`docs/debt-register.md`](docs/debt-register.md) and
[`docs/bug-diary.md`](docs/bug-diary.md). Five annotated agent-session
transcripts are in [`transcripts/`](transcripts/). `Report.md` holds the team
process report and the five members' reflections.

## GitHub

<https://github.com/298994923/TradingAgents-Teamwork>

## License

This repository is distributed under the Apache License 2.0. The upstream
copyright and licence notices are retained in [`LICENSE`](LICENSE); the team's
modifications are released under the same licence.
