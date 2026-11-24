"""CLI --variant bug: omitted vs explicit v0, v1 forwarding, v2 rejection.

Behaviour after the fix:

- Omitting ``--variant`` keeps the configured rounds (legacy run), not a forced
  preset, and records the configured depth.
- Explicit ``v0`` runs the v0 preset (2 pairs) and the manifest records the
  **effective** depth 2 and variant v0.
- Explicit ``v1`` is forwarded to the graph (not rejected in main.py), runs 1 pair,
  and is recorded as v1 / depth 1.
- Explicit ``v2`` is rejected before any model call: zero model calls, no manifest.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

import cli.main as m
import cli.run as cli_run

FIXED_AT = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)

# Preset: explicit v0 -> 2 pairs, v1 -> 1 pair; omitted (no workflow_variant) keeps
# the configured depth. Mirrors C's candidate graph, which applies the preset and
# reports effective settings through run_settings().
_PRESETS = {"v0": 2, "v1": 1}


class PresetGraph:
    def __init__(self, analysts=None, config=None, debug=False, callbacks=None, workflow_variant=None):
        self.config = dict(config or {})
        self.selected_analysts = analysts or []
        self.workflow_variant = workflow_variant
        if workflow_variant in _PRESETS:
            # ADR-006: a preset changes only max_debate_rounds; risk rounds keep the
            # configured value.
            self.config["max_debate_rounds"] = _PRESETS[workflow_variant]
        self.model_calls = 0

    def run_settings(self):
        settings = {
            "version": "0.7.1",
            "max_debate_rounds": self.config.get("max_debate_rounds"),
            "max_risk_discuss_rounds": self.config.get("max_risk_discuss_rounds"),
        }
        if self.workflow_variant is not None:
            settings["workflow_variant"] = self.workflow_variant
        return settings


# --- effective config / variant helpers -------------------------------------


def test_effective_config_overlays_run_settings_rounds():
    graph = PresetGraph(config={"max_debate_rounds": 3, "max_risk_discuss_rounds": 3},
                        workflow_variant="v0")
    effective = cli_run._effective_config({"max_debate_rounds": 3, "max_risk_discuss_rounds": 3}, graph)
    assert effective["max_debate_rounds"] == 2
    assert effective["max_risk_discuss_rounds"] == 3


def test_effective_config_keeps_config_when_omitted():
    graph = PresetGraph(config={"max_debate_rounds": 3, "max_risk_discuss_rounds": 3},
                        workflow_variant=None)
    effective = cli_run._effective_config({"max_debate_rounds": 3, "max_risk_discuss_rounds": 3}, graph)
    assert effective["max_debate_rounds"] == 3


# --- manifest records effective depth ---------------------------------------


def test_explicit_v0_manifest_records_effective_two_rounds(tmp_path, monkeypatch):
    captured = {}

    def fake_write(**kwargs):
        captured.update(kwargs)
        return tmp_path / "manifest.json"

    monkeypatch.setattr(cli_run, "write_run_manifest", fake_write)

    class _Stats:
        def get_stats(self):
            return {"llm_calls": 0, "tool_calls": 0, "tokens_in": None, "tokens_out": None}

    graph = PresetGraph(config={"max_debate_rounds": 3}, workflow_variant="v0")
    variant = cli_run._effective_manifest_variant(graph, "v0")
    effective = cli_run._effective_config(
        {"results_dir": str(tmp_path), "max_debate_rounds": 3}, graph, variant
    )
    write = cli_run._make_manifest_writer(
        effective,
        {"ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock"},
        _Stats(),
        variant=variant,
    )
    write(failure=None, outcome="Buy")
    assert captured["variant"] == "v0"
    assert captured["config"]["max_debate_rounds"] == 2


# --- config_snapshot records workflow_variant (data-contract promise) -------


def _write_real_manifest(tmp_path, requested):
    """Run the real recorder path and return (manifest, run_id_first_segment)."""
    from tradingagents.run_recorder import read_manifest

    graph = PresetGraph(config={"max_debate_rounds": 3}, workflow_variant=requested)
    variant = cli_run._effective_manifest_variant(graph, requested or "v0")
    effective = cli_run._effective_config(
        {"results_dir": str(tmp_path), "max_debate_rounds": 3}, graph, variant
    )

    class _Stats:
        def get_stats(self):
            return {"llm_calls": 0, "tool_calls": 0, "tokens_in": None, "tokens_out": None}

    write = cli_run._make_manifest_writer(
        effective,
        {"ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock"},
        _Stats(),
        variant=variant,
    )
    path = write(failure=None, outcome="Buy")
    manifest = read_manifest(path)
    return manifest, manifest["run_id"].split("-", 1)[0]


def test_snapshot_workflow_variant_v0(tmp_path):
    manifest, _ = _write_real_manifest(tmp_path, "v0")
    assert manifest["config_snapshot"]["workflow_variant"] == "v0"


def test_snapshot_workflow_variant_v1(tmp_path):
    manifest, _ = _write_real_manifest(tmp_path, "v1")
    assert manifest["config_snapshot"]["workflow_variant"] == "v1"


def test_snapshot_workflow_variant_omitted_is_v0(tmp_path):
    manifest, _ = _write_real_manifest(tmp_path, None)
    assert manifest["config_snapshot"]["workflow_variant"] == "v0"


def test_snapshot_variant_matches_run_id_first_segment(tmp_path):
    for requested in ("v0", "v1", None):
        manifest, segment = _write_real_manifest(tmp_path, requested)
        assert manifest["config_snapshot"]["workflow_variant"] == segment


# --- main.py: omitted vs explicit, v1 passes through, v2 rejected -----------


def _runner(monkeypatch):
    calls = []
    monkeypatch.setattr(m, "run_analysis", lambda **kw: calls.append(kw))
    return CliRunner(), calls


def test_omitted_flag_passes_none(monkeypatch):
    runner, calls = _runner(monkeypatch)
    assert runner.invoke(m.app, []).exit_code == 0
    assert calls[0]["variant"] is None


def test_explicit_v0_passes_v0(monkeypatch):
    runner, calls = _runner(monkeypatch)
    assert runner.invoke(m.app, ["--variant", "v0"]).exit_code == 0
    assert calls[0]["variant"] == "v0"


def test_explicit_v1_reaches_run_analysis(monkeypatch):
    runner, calls = _runner(monkeypatch)
    assert runner.invoke(m.app, ["--variant", "v1"]).exit_code == 0
    assert calls[0]["variant"] == "v1"


def test_explicit_v2_rejected_in_main(monkeypatch):
    runner, calls = _runner(monkeypatch)
    assert runner.invoke(m.app, ["--variant", "v2"]).exit_code != 0
    assert calls == []


# --- run_analysis: v2 refused before any model call / manifest -------------


def test_run_analysis_v2_zero_calls_no_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADINGAGENTS_RESULTS_DIR", str(tmp_path))
    created = []

    class _Never:
        def __init__(self, *a, **k):
            created.append(True)

    monkeypatch.setattr(cli_run, "TradingAgentsGraph", _Never)
    with pytest.raises(cli_run.typer.Exit):
        cli_run.run_analysis(flags={}, variant="v2")
    assert created == []
    assert list(tmp_path.rglob("manifest.json")) == []


def test_omitted_is_legacy_not_forced_preset():
    # None means "omitted": no workflow_variant is forwarded and no rejection.
    cli_run._reject_unavailable_variant(None, PresetGraph)  # must not raise
    graph = cli_run._build_graph(PresetGraph, ["market"], {"max_debate_rounds": 3}, None,
                                 workflow_variant=None)
    assert graph.workflow_variant is None
    assert graph.config["max_debate_rounds"] == 3


def test_v1_forwarded_to_supporting_graph():
    graph = cli_run._build_graph(PresetGraph, ["market"], {"max_debate_rounds": 3}, None,
                                 workflow_variant="v1")
    assert graph.workflow_variant == "v1"
    assert graph.config["max_debate_rounds"] == 1
