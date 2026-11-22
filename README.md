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

The upstream baseline is complete and green. Team-owned governance and
extension modules are being added in small, reviewed steps. `AGENTS.md` marks
paths that do not exist yet with `[TBD]`; a document describing a feature does
not mean the feature is implemented. The table in
[CI and blocking gates](#ci-and-blocking-gates) is the authoritative summary of
what is enforced today.

| Item | Current value |
|---|---|
| Python | 3.12 (baseline measured on 3.12.16) |
| Upstream baseline | `TauricResearch/TradingAgents@9fa1196` |
| License | Apache License 2.0 (see `LICENSE`) |
| Offline tests | `1441 passed, 1 skipped, 1 deselected` |
| Lint | `ruff check src tests test` clean |
| CI checks | `tests`, `lint`, `schema`, `test-approval`, `ai-use-log` |

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

## Upstream baseline and team additions

The repository imports the upstream project at commit `9fa1196` and moves the
packages into a `src/` layout without rewriting their behaviour. The migration
commit is `b5d2f67`; the frozen test baseline is documented in
[`docs/evaluation/baseline.md`](docs/evaluation/baseline.md).

The team work is organised by role:

| Role | Responsibility |
|---|---|
| A | Evidence: requirement registry, evidence records and time validity |
| B | Collaboration: independent claims, targeted responses, layered context |
| C | Workflow: scheduling, execution budget, bounded loops, resume |
| D | Deterministic safety: hard invariants, final validation, permissions |
| E | Run records, experiments, CI blocking gates, delivery |

Most of these extension modules are still being implemented; the current
repository contains the upstream baseline, the E-owned RunEvent recorder, and the
governance entry points. When a module lands, its contract and tests land with
it.

## Architecture

The main entry point is `TradingAgentsGraph` in
[`src/tradingagents/graph/trading_graph.py`](src/tradingagents/graph/trading_graph.py).
It wires graph setup, propagation, conditional routing, checkpointing and the
agents. The CLI in [`src/cli/`](src/cli) owns interactive selection, display and
the run loop; `src/cli/stats_handler.py` tracks LLM/tool calls and token usage.

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
  blocked result into a pass. The D-owned invariants and validation contracts
  are being added.
- **Run records.** [`src/tradingagents/run_recorder.py`](src/tradingagents/run_recorder.py)
  serialises a run manifest with a versioned schema (15 fields: run identity,
  config, prompt hashes, evidence snapshot, usage, duration, failure, stop
  reason). The recorder is deterministic, refuses to overwrite, and excludes
  secret-shaped config keys. The contract is
  [`docs/contracts/run-event.md`](docs/contracts/run-event.md). Wiring the
  recorder into the CLI/graph is a later step because it depends on C's
  `stop_reason` domain.
- **Context and memory.** The upstream memory log is retained. B's layered
  context builder, compression threshold and constraint re-injection policy are
  being added.

## Repository layout

```text
TradingAgents-Coursework/
├── AGENTS.md                    coding-agent entry point and code map
├── Prompt.md                    static, plan-first startup prompt (D9)
├── README.md
├── pyproject.toml               src layout, entry point, pytest/ruff config
├── Dockerfile / docker-compose.yml
├── .agent/rules.md              project covenant
├── .github/workflows/ci.yml     blocking CI
├── docs/
│   ├── ai-use-log.yaml          per-PR AI-use log
│   ├── contracts/run-event.md   RunEvent manifest contract
│   ├── evaluation/baseline.md   V0 baseline evidence
│   ├── plans/                   versioned plans (E)
│   └── req/req-schema.json      requirements-schema proposal (not adopted)
├── src/
│   ├── cli/                     Typer CLI and display
│   └── tradingagents/           graph, agents, dataflows, llm_clients, memory
├── test/
│   ├── offline/                 deterministic tests (new code)
│   └── live/                    API-dependent tests (reserved)
└── tests/                       upstream regression suite
```

Some directories are not here yet: `docs/architecture/`, `docs/code-governance/`,
`prompts/` and `transcripts/`. They will be added when the team has real content
for them, not as empty placeholders.

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

# API-dependent tests (when test/live/ contains any; keys required)
python -m pytest test/live -m integration -q

# Static checks
ruff check src tests test scripts
```

Current local results (2026-11-22): `1441 passed, 1 skipped, 1 deselected` for
the full offline suite; `17 passed` for the CI-gate tests. The one skip is
optional `langchain_aws` not being installed. `test/live/` is empty, so there is
**no** live-test pass to report; a suite that was not run is not a suite that
passed.

## CI and blocking gates

CI runs on every pull request and on pushes to `main`
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)). The workflow has five
jobs. Two of them only make sense for a PR and skip on a plain push.

Here is what each gate actually does today, in plain words:

- **`tests`** — runs the upstream `tests/` and our `test/offline/`. If a test
  fails, the PR is blocked. That's all: it does not count tests or compare
  against an old number.
- **`lint`** — runs ruff, compiles the code to catch syntax errors, and checks
  that every third-party import is declared in `pyproject.toml`. A few packages
  that the upstream code already gets through its dependencies are allowlisted.
- **`schema`** — checks `docs/req/requirements.yaml` against
  `docs/req/req-schema.json`. The check is real, but the registry is only a
  one-entry seed written by E; A will replace it with the real requirements.
- **`test-approval`** — if a PR changes a file under `src/`, that file must be
  listed in `docs/approvals.yaml` with an approver and a date. No matching
  record, no merge. It only covers `src/`, and the approver is just a name in
  the file — we do not check who actually approved it.
- **`ai-use-log`** — if a PR changes `src/`, `scripts/` or `test/`, it must add
  a new entry to `docs/ai-use-log.yaml` with a fresh unique id and
  `human_reviewed: true`. Editing only docs, prompts or `.github/` does not
  trigger it.

To be honest about the state: `tests`, `lint` and `ai-use-log` are real gates
that will block a bad PR. `test-approval` and `schema` work but run on simple
seed data. The semantic-evaluation gate (course gate 4) is **not implemented** —
an earlier placeholder was removed because it was not real evaluation. There is
a TODO in [`docs/plans/E-ci-gates.md`](docs/plans/E-ci-gates.md): it needs a real
eval runner and a fixed evaluation set from B. We do not claim all six course
gates are finished.

Branch protection on `main` is enabled. Safety-critical paths are still
expected to require human review and an architecture decision. `CODEOWNERS`
and per-path permission checks are part of D's governance work and will be
added when the permission model lands, not as an empty placeholder.

## Baseline and reproducibility

- Upstream: `TauricResearch/TradingAgents@9fa1196`, Apache-2.0.
- Migration to `src/`: commit `b5d2f67`.
- Frozen V0 test baseline: commit `b5d2f67`, Python 3.12.16, `1412 passed,
  1 skipped, 1 deselected`.
- Current additions do not replace the upstream suite; they extend it under
  `test/offline/`.

The exact commands and environment for the V0 baseline are recorded in
[`docs/evaluation/baseline.md`](docs/evaluation/baseline.md). Experiments are
recorded as run manifests (version, input, config, prompt hashes, usage,
duration, failure, stop reason) so comparisons are tied to a version rather
than to a screenshot.

## GitHub

<https://github.com/298994923/TradingAgents-Teamwork>

## Governance

Read, in order: [`AGENTS.md`](AGENTS.md) → [`Prompt.md`](Prompt.md) →
[`.agent/rules.md`](.agent/rules.md). The workflow is plan first, stop for human
approval, then implement in small steps with tests. Every code or prompt change
gets an AI-use log entry; every feature gets at least one negative test; changes
to safety-critical paths require an architecture decision and human approval.
Do not weaken or delete tests to make CI pass.

## License

This repository is distributed under the Apache License 2.0. The upstream
copyright and licence notices are retained in [`LICENSE`](LICENSE); the team's
modifications are released under the same licence.
