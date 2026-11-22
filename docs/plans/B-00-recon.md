# Package B reconnaissance

FuKaichao, 60468706. Upstream baseline 9fa1196fffbcfd9de5146d2dd2869df84ab99838. Team main snapshot 3b23a8de5aa433be0174d6439885396b920aa902. Paths below refer to the team snapshot. The team provenance record identifies the upstream source and migration at docs/upstream/PROVENANCE.md:5-13. This report was prepared in the local feature branch using the GitHub source archive because Git fetch timed out.

| Item | Finding | Evidence | Impact |
|---|---|---|---|
| 1. Layout | Team package uses src/tradingagents. Under it, review.py and context_builder.py are absent. Existing targets are agents/researchers/bull_researcher.py, agents/researchers/bear_researcher.py, agents/managers/research_manager.py and agents/schemas.py. | Team Git tree at the pinned SHA; pyproject.toml:51; researcher factories at line 9, manager at line 14, ResearchPlan at schemas.py:95 | Work against team paths. |
| 2. State | AgentState carries identity/date, four reports, investment debate and plan, trader plan, risk debate, final decision/rating, memory and portfolio context. Nested investment state holds bull_history, bear_history, history, current_response and count. | src/tradingagents/agents/state.py:8,45; researcher updates at bull_researcher.py:56 and bear_researcher.py:58; manager reads at research_manager.py:19 | C owns any new shared fields. |
| 3. Visibility and rounds | Both researchers interpolate shared history, append their response and increment count. C's routing compares count with twice the configured maximum. | bull_researcher.py:46,56; bear_researcher.py:48,58; src/tradingagents/graph/conditional_logic.py:16 | A second speaker can see the first answer; test the actual model input. |
| 4. Manager | Reads instrument context and debate history, binds ResearchPlan, renders a plan with text fallback and writes investment_plan. | research_manager.py:14,19,53,71 | Preserve the legacy string interface. |
| 5. LLM | create_llm_client(provider, model, base_url=None, **kwargs); researcher calls llm.invoke(prompt). Client factory passes configured max_retries. Callback accepts two provider usage shapes. | src/tradingagents/llm_clients/factory.py:7,123; bull_researcher.py:51; src/cli/stats_handler.py:75,89 | Transport retries and B's single format repair need separate counters. Live CityU response metadata is unverified. |
| 6. Validation | Pydantic ResearchPlan and structured-to-text fallback exist; no B claim validator located. | agents/schemas.py:95; agents/structured.py:42,59,84 under src/tradingagents | Fallback text alone cannot establish reference validity. |
| 7. Evidence | evidence.py and its ID-validation signature not found in the team tree. | Recursive team Git tree at pinned SHA | Request A's interface; use an injected checker in offline tests. |
| 8. Tests | test/offline and test/live exist; live contains only .gitkeep. No tests/ or test/fixtures/ in the team tree. | Directory listing; pyproject.toml:63-64; test/offline/conftest.py:59 | Offline default excludes integration. |
| 9. Prompts and rules | AGENTS.md, Prompt.md and both v1.0 and v1.1 YAML files already exist. | Team tree; AGENTS.md:12-21 | Reconcile existing content before editing; filenames alone do not establish evaluated versions. |
| 10. Environment | Temporary isolated interpreter has pydantic 2.14.4, jsonschema 4.26.0, tiktoken 0.14.0. | importlib.metadata.version on the test interpreter | No dependency change to the repository. |
| 11. Output ownership | Team runner uses plural results and outputs. Both ignored. NanLi authored the metric implementation in 47545b6ca2. | .gitignore:11-12; run_test.py:29-30; reporting.py history via GitHub commits API | Repeated ticker/date runs overwrite the same manifest. Formal extension approval remains open. |
| 12. Metrics | One manifest per save, nested by ticker/date. Run and node aggregates. | run_test.py:96-115,125; src/tradingagents/reporting.py:219,262-263 | See field table below. No verified consumer from future C/E packages. |
| 13. Reuse | Existing callback counts model usage and inclusive node time; run_test separately measures elapsed time. | src/cli/stats_handler.py:130,147,165,194; run_test.py:99,112 | Aggregate estimates to matching invocations/nodes before comparison. |
| 14. Baseline | Factories return callable state nodes and accept an injected LLM. Both original offline suites executed; see results below. | bull_researcher.py:9; bear_researcher.py:9; research_manager.py:14 | Preserve originals; a real model was not invoked. |
| 15. Historical data | No tracked results or outputs in the team tree. not_delivered_doc/baseline.metric is a TODO. | Team tree; not_delivered_doc/baseline.metric:1; docs/upstream/PROVENANCE.md:19-22 | No historical measured comparison identified. |

## Directories and metric semantics

Writer: src/tradingagents/reporting.py:219-264. Implementation author: NanLi, commit 47545b6ca2. Runtime path: results/<ticker>/<trade_date>/metrics.json. Run ID is generated at second resolution; the pathname does not contain it. Preserve a run-specific copy before the next comparison run. Planned B artifacts: outputs/B/<run_id>/ for raw data, results/B/ for sanitized tables. Both directories are ignored; coordinate publication of selected results with E.

| Fields | Meaning and source | Evaluation use | Readable by B |
|---|---|---|---|
| schema_version, run_id, ticker, trade_date, status | Writer-generated metadata or caller inputs, reporting.py:242-253 | Grouping and comparability | Yes |
| started_at, finished_at, duration_sec | Caller wall clock, run_test.py:99-112; finish defaults to generation time, reporting.py:241 | Run duration when supplied | Yes |
| run_settings | Snapshot including deep and quick model names, graph/trading_graph.py:255-268 | Match settings | Yes |
| usage_source | Callback reports provider or none, src/cli/stats_handler.py:194-203 | Eligibility check; partial provider coverage can still report provider | Yes |
| totals: llm_calls, tool_calls, tokens_in, tokens_out, tokens_total | Callback counts, normalized in reporting.py:151-161 | Calls and provider tokens when coverage verified | Yes |
| by_node: llm_calls, tokens_in, tokens_out, tokens_total | Aggregated by node, reporting.py:164-178 | Node totals; repeated rounds share a bucket | Yes |
| timing: duration_sec, by_node_sec | Inclusive elapsed time, reporting.py:180-191 | Compare at the recorded granularity | Yes |
| cost: cost_usd, pricing_source, conditional currency/input_per_1m/output_per_1m | Supplied rates times usage; otherwise null cost, reporting.py:194-212 | Conditional estimate | Yes |
| artifacts: report_md, report_html | Report names, reporting.py:260 | Locate related evidence | Yes |

No per-layer, per-round or per-invocation token fields were found. Compare summed estimated input tokens with input tokens only. Include system and formatting overhead, isolate repair calls, and mark unknown or incomplete usage unavailable. Do not interpret normalized zero as proof of zero consumption.

## Executed verification

- Upstream: python -m pytest tests -p no:cacheprovider -q -m 'not integration' produced 1412 passed, 1 skipped, 1 deselected, 24 warnings, 100 subtests passed in 8.99s.
- Team archive: PYTHONPATH=src python -m pytest test/offline -q -m 'not integration' produced 1423 passed, 1 skipped, 1 deselected, 24 warnings, 100 subtests passed in 8.37s. The first sandboxed attempt produced 7 failed and 1416 passed; all seven were local sign-in socket permission failures. The run with loopback permission used the same tests.
- The skip was optional langchain_aws; integration was deselected. No live model call. The migration note's historical count is separate from both observations.

## Missing fields and interface requests

1. C: please provide collaboration mode, round/phase, speaker, eligible target IDs and a versioned claim ledger with unresolved questions. C retains routing, round limits and checkpoint ownership. Keep legacy fields available. Confirm the resume contract.
2. A: please confirm the evidence checker signature, unknown-time handling and error representation. The source snapshot contains no concrete evidence.py.
3. D: confirm the source and stable identifiers for hard constraints. B needs exact post-compaction retention checks.
4. E and NanLi: confirm the formal metric schema approver and the method for publishing sanitized summaries under the ignored results directory. B can use a run-specific sidecar for estimates and linkage.
5. Team: confirm ownership of the pre-existing prompt files before any replacement or version change. No measured evidence for a v1.1 change was identified.
Local baseline tag: baseline-pre-b-20261120 (verified during S7).
