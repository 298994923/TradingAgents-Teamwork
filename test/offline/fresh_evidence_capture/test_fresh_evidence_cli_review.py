"""Test-first fresh capture through real Typer, graph, Evidence and recorder."""

import hashlib
import json
import os
import time
from copy import deepcopy
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from types import SimpleNamespace

import pytest
from assertions import assert_fresh_capture, assert_no_published_reference
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from typer.testing import CliRunner

import cli.run as cli_run
from cli.main import app
from cli.models import AnalystType
from tests import test_graph_end_to_end as graph_fixture
from tradingagents import evidence_store
from tradingagents.evidence import EvidenceError
from tradingagents.run_recorder import read_manifest

pytestmark = pytest.mark.unit
offline = graph_fixture.offline
INPUTS = json.loads(Path(__file__).with_name("inputs.json").read_text(encoding="utf-8"))
REPORTS = {key: INPUTS["analyst_outputs"][key] for key in ("market", "social")}
CONTEXT = INPUTS["context"]
CAPTURE_TIME = datetime.fromisoformat(INPUTS["captured_at"])
INJECTED_ERROR = "injected Evidence publication failure"


class ReportModel(graph_fixture.TimedModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        step = (run_manager.metadata or {}).get("langgraph_node") if run_manager else None
        if step != "agent":
            return super()._generate(messages, stop, run_manager, **kwargs)
        prompt = "\n".join(str(message.content) for message in messages)
        # The actual Market turn binds tools; the Sentiment fallback does not.
        key = "market" if self.tools else "social"
        when = time.monotonic()
        self.seen.append((step, prompt, when, when))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=REPORTS[key]))])


def _cli(monkeypatch, tmp_path, variant, *, capture, fail_save=False):
    monkeypatch.setattr(cli_run, "unattended_gaps", lambda flags: [])
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags: {
        "ticker": INPUTS["ticker"], "analysis_date": INPUTS["trade_date"], "asset_type": "stock",
        "analysts": [AnalystType.MARKET, AnalystType.SOCIAL], "research_depth": 3,
        "llm_provider": "openai", "quick_think_llm": "offline", "deep_think_llm": "offline",
        "backend_url": None,
    })
    monkeypatch.setattr(cli_run, "message_buffer", type(cli_run.message_buffer)())
    config = deepcopy(cli_run.DEFAULT_CONFIG)
    config.update(
        results_dir=str(tmp_path / "results"), data_cache_dir=str(tmp_path / "cache"),
        memory_log_path=str(tmp_path / "memory.md"), guard_enabled=False, evidence_mode="strict",
    )
    monkeypatch.setattr(cli_run, "DEFAULT_CONFIG", config)
    monkeypatch.delenv("TRADINGAGENTS_MAX_DEBATE_ROUNDS", raising=False)
    monkeypatch.setenv("TRADINGAGENTS_MAX_RISK_ROUNDS", "1")
    model = ReportModel(cache=False)
    graph_type = graph_fixture.trading_graph.TradingAgentsGraph
    monkeypatch.setattr(
        graph_fixture.trading_graph, "create_tier_client",
        lambda *args, **kwargs: graph_fixture._Client(model),
    )
    monkeypatch.setattr(graph_type, "resolve_instrument_context",
                        lambda *args: CONTEXT["instrument_context"])

    reservations, chunks, final, links, memory, decisions = [], [], [], [], [], []
    clock_reads, publications, published_counts, destinations = [], [], [], []

    class CaptureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:  # Leave unrelated, naive report-path timestamps alone.
                return datetime.now()
            clock_reads.append(tz)
            return CAPTURE_TIME.astimezone(tz)

    monkeypatch.setattr(graph_fixture.trading_graph, "datetime", CaptureClock)
    reserve, stream, finalize = cli_run.reserve_run_id, graph_type.stream_run, cli_run._finalize_run_manifest
    link, memory_step, record = os.link, graph_type._memory_step, graph_type.record_decision
    destination = evidence_store.evidence_destination

    @wraps(destination)
    def observe_destination(config, run_id, artifact_key):
        path = destination(config, run_id, artifact_key)
        destinations.append((run_id, artifact_key, path))
        return path

    @wraps(reserve)
    def observe_reservation(**kwargs):
        run_id = reserve(**kwargs)
        reservations.append(run_id)
        return run_id

    @wraps(stream)
    def observe_stream(self, *args, **kwargs):
        for messages, chunk in stream(self, *args, **kwargs):
            chunks.append(deepcopy(chunk))
            published_counts.append(len(publications))
            yield messages, chunk

    @wraps(finalize)
    def observe_finalization(**kwargs):
        final.append((deepcopy(kwargs["final_state"]), kwargs["failure"]))
        return finalize(**kwargs)

    @wraps(memory_step)
    def observe_memory(self, state):
        result = memory_step(self, state)
        memory.append(True)
        return result

    @wraps(record)
    def observe_decision(self, *args, **kwargs):
        decisions.append(True)
        return record(self, *args, **kwargs)

    def observe_link(source, destination, *args, **kwargs):
        path = Path(destination)
        if not path.is_relative_to(tmp_path) or "evidence" not in path.parts or path.parent.name != "v1":
            return link(source, destination, *args, **kwargs)
        # Observe the real A publication boundary without changing the manifest writer.
        links.append((path, tuple(memory), tuple(n for n, *_ in model.seen)))
        if fail_save:
            raise OSError(INJECTED_ERROR)
        result = link(source, destination, *args, **kwargs)
        publications.append(path)
        return result

    monkeypatch.setattr(cli_run, "reserve_run_id", observe_reservation)
    monkeypatch.setattr(cli_run, "_finalize_run_manifest", observe_finalization)
    monkeypatch.setattr(graph_type, "stream_run", observe_stream)
    monkeypatch.setattr(graph_type, "_memory_step", observe_memory)
    monkeypatch.setattr(graph_type, "record_decision", observe_decision)
    monkeypatch.setattr(evidence_store, "evidence_destination", observe_destination)
    monkeypatch.setattr(os, "link", observe_link)

    args = [
        "--ticker", INPUTS["ticker"], "--date", INPUTS["trade_date"], "--analysts", "market,social",
        "--no-checkpoint", "--no-save", "--no-show", "--no-html", "--variant", variant,
    ]
    result = CliRunner().invoke(app, [*args, "--capture-evidence"] if capture else args)
    [run_id] = reservations
    runs = tmp_path / "results" / "runs"
    assert {p.name for p in runs.iterdir()} == {run_id}
    assert not (tmp_path / "cache" / "checkpoints").exists()
    [(state, failure)] = final
    root = runs / run_id
    manifest_path = root / "manifest.json"
    manifest = read_manifest(manifest_path)
    sidecar = json.loads((root / "evidence-mode.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == sidecar["run_id"] == run_id
    return SimpleNamespace(
        result=result, state=state, failure=failure, manifest=manifest, manifest_path=manifest_path,
        sidecar=sidecar, root=root, run_id=run_id, chunks=chunks, links=links, decisions=decisions,
        model=model, clock_reads=clock_reads, published_counts=published_counts, destinations=destinations,
    )


def _assert_route(run, variant, pairs):
    if run.result.exception is not None:
        raise run.result.exception
    assert run.result.exit_code == 0 and run.failure is None and run.manifest["failure"] is None
    assert run.state["final_rating"] == run.manifest["outcome"] == "Overweight"
    assert run.state["stop_reason"] == run.manifest["stop_reason"] == "completed"
    assert run.manifest["config_snapshot"]["workflow_variant"] == variant
    assert run.manifest["config_snapshot"]["max_debate_rounds"] == pairs
    assert run.decisions == [True]
    assert run.state["market_report"] == REPORTS["market"]
    assert run.state["sentiment_report"] == REPORTS["social"]
    assert [node for node, *_ in run.model.seen] == [
        "agent", "agent", *(["Bull Researcher", "Bear Researcher"] * pairs),
        "Research Manager", "Trader", "Aggressive Analyst", "Conservative Analyst",
        "Neutral Analyst", "Portfolio Manager",
    ]
    roles = {"Bull Researcher": "bull", "Bear Researcher": "bear", "Research Manager": "research_manager"}
    receipts = json.loads((run.root / "prompt_receipts.json").read_text(encoding="utf-8"))
    assert receipts["run_id"] == run.run_id
    assert [(x["role"], x["input_sha256"]) for x in receipts["calls"]] == [
        (roles[node], hashlib.sha256(prompt.encode()).hexdigest())
        for node, prompt, *_ in run.model.seen if node in roles
    ]


@pytest.mark.parametrize(("variant", "pairs"), [("v0", 2), ("v1", 1)])
def test_fresh_capture_v0_v1(monkeypatch, tmp_path, offline, variant, pairs):
    """A-EV-02/05/08: real report bytes, matching reference and canonical artifact."""
    run = _cli(monkeypatch, tmp_path, variant, capture=True)
    _assert_route(run, variant, pairs)
    ref = run.state["evidence_snapshot"]
    [(path, memory, prior_nodes)] = run.links
    assert len(memory) == 1 and prior_nodes == ("agent", "agent")
    assert run.clock_reads == [UTC]
    assert_fresh_capture(
        final_state=run.state, manifest_path=run.manifest_path, artifact_root=run.root / "evidence",
        expected_run_id=run.run_id, expected_capture_time=INPUTS["captured_at"],
        expected_reports=REPORTS, expected_context=CONTEXT,
    )
    assert path == run.root / "evidence" / ref["artifact_key"]
    assert run.destinations == [(run.run_id, ref["artifact_key"], path)]
    assert list((run.root / "evidence").rglob("*.json")) == [path]
    assert {k: ref[k] for k in ("snapshot_id", "artifact_key")} == run.sidecar["snapshot_ref"]
    observed = [
        (chunk["evidence_snapshot"], count)
        for chunk, count in zip(run.chunks, run.published_counts, strict=True)
        if chunk.get("evidence_snapshot") is not None
    ]
    assert observed and all(item == (ref, 1) for item in observed)


def test_capture_off_preserves_v1(monkeypatch, tmp_path, offline):
    run = _cli(monkeypatch, tmp_path, "v1", capture=False)
    _assert_route(run, "v1", 1)
    assert_no_published_reference(final_state=run.state, manifest_path=run.manifest_path)
    assert run.sidecar["snapshot_ref"] == {"snapshot_id": None, "artifact_key": None}
    assert {"capture_context", "source_run_id", "evidence_snapshot", "evidence_diagnostics"}.isdisjoint(run.state)
    assert not run.links and not run.clock_reads and not run.destinations
    assert not (run.root / "evidence").exists()


def test_save_failure_aborts_before_bull(monkeypatch, tmp_path, offline):
    """A-EV-05: failed real publication sends no usable reference."""
    run = _cli(monkeypatch, tmp_path, "v1", capture=True, fail_save=True)
    assert run.result.exit_code != 0
    error = run.result.exception
    assert error is run.failure
    assert not run.decisions and run.state is None
    assert all(chunk.get("evidence_snapshot") is None for chunk in run.chunks)
    assert_no_published_reference(final_state={}, manifest_path=run.manifest_path)
    assert run.manifest["failure"] == str(error)
    assert run.manifest["outcome"] is None and run.manifest["stop_reason"] is None
    assert run.sidecar["snapshot_ref"] == {"snapshot_id": None, "artifact_key": None}
    assert isinstance(error, EvidenceError), repr(error)
    assert error.code == "IO_ERROR"
    assert isinstance(error.__cause__, OSError) and str(error.__cause__) == INJECTED_ERROR
    [(path, memory, prior_nodes)] = run.links
    assert len(memory) == 1 and prior_nodes == ("agent", "agent")
    assert run.destinations == [(run.run_id, f"v1/{path.name}", path)]
    assert [node for node, *_ in run.model.seen] == ["agent", "agent"]
    assert not path.exists() and not list(path.parent.glob(".evidence-*.tmp"))
