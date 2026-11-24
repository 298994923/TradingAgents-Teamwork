"""Variant forwarding: detect workflow_variant support instead of a config key.

The old gate read a ``config["workflow_variant"]`` key that never existed, so v1/v2
were always refused. New rule:

- v0 is always allowed.
- v2 is refused before any model call (not delivered yet).
- v1 is allowed only when ``TradingAgentsGraph.__init__`` accepts a
  ``workflow_variant`` keyword; the value is forwarded to the graph.
- The manifest run_id and config_snapshot use the variant the graph's
  ``run_settings()`` reports (falling back to the requested one when absent).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import cli.run as cli_run

FIXED_AT = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


class _SupportsVariant:
    """Stub graph whose __init__ accepts workflow_variant and reports it."""

    def __init__(self, analysts=None, config=None, debug=False, callbacks=None, workflow_variant="v0"):
        self.config = config or {}
        self.selected_analysts = analysts or []
        self.workflow_variant = workflow_variant
        self.received_variant = workflow_variant

    def run_settings(self):
        return {"version": "0.7.1", "workflow_variant": self.workflow_variant}


class _NoVariant:
    """Stub graph whose __init__ does NOT accept workflow_variant."""

    def __init__(self, analysts=None, config=None, debug=False, callbacks=None):
        self.config = config or {}
        self.selected_analysts = analysts or []

    def run_settings(self):
        return {"version": "0.7.1"}


def _graph_cls_without_kwargs():
    class _Strict:
        def __init__(self, analysts=None, config=None, debug=False, callbacks=None):
            pass

        def run_settings(self):
            return {}

    return _Strict


# --- signature detection ----------------------------------------------------


def test_detects_explicit_keyword():
    assert cli_run._graph_accepts_workflow_variant(_SupportsVariant) is True


def test_detects_absence():
    assert cli_run._graph_accepts_workflow_variant(_NoVariant) is False


def test_var_kwargs_alone_is_not_support():
    # A legacy graph that swallows unknown kwargs must NOT be treated as supporting
    # workflow_variant: it would accept v1 and silently ignore it (mislabelling).
    class _VarKwargs:
        def __init__(self, **kwargs):
            self.received = dict(kwargs)

    assert cli_run._graph_accepts_workflow_variant(_VarKwargs) is False


def test_legacy_var_kwargs_graph_refuses_v1_and_does_not_forward():
    class _Legacy:
        def __init__(self, selected_analysts=None, *args, **kwargs):
            self.received = dict(kwargs)

        def run_settings(self):
            return {}

    # v1 is refused before construction ...
    with pytest.raises(cli_run.typer.Exit):
        cli_run._reject_unavailable_variant("v1", _Legacy)
    # ... and v0 construction never forwards a workflow_variant.
    graph = cli_run._build_graph(_Legacy, ["market"], {}, None, workflow_variant="v0")
    assert "workflow_variant" not in graph.received


# --- refusal rules -----------------------------------------------------------


def test_v0_always_allowed():
    cli_run._reject_unavailable_variant("v0", _NoVariant)  # no raise


def test_v2_refused_even_when_graph_supports_variant():
    with pytest.raises(cli_run.typer.Exit):
        cli_run._reject_unavailable_variant("v2", _SupportsVariant)


def test_v1_refused_when_graph_has_no_variant():
    with pytest.raises(cli_run.typer.Exit):
        cli_run._reject_unavailable_variant("v1", _NoVariant)


def test_v1_allowed_when_graph_supports_variant():
    cli_run._reject_unavailable_variant("v1", _SupportsVariant)  # no raise


# --- forwarding --------------------------------------------------------------


def test_forward_variant_when_supported():
    graph = cli_run._build_graph(
        _SupportsVariant, ["market"], {}, None, workflow_variant="v1"
    )
    assert graph.received_variant == "v1"


def test_do_not_forward_variant_when_unsupported():
    graph = cli_run._build_graph(_NoVariant, ["market"], {}, None, workflow_variant="v0")
    # Construction succeeded without the keyword.
    assert isinstance(graph, _NoVariant)


# --- effective manifest variant ---------------------------------------------


def test_effective_variant_from_run_settings():
    graph = _SupportsVariant(workflow_variant="v1")
    assert cli_run._effective_manifest_variant(graph, "v0") == "v1"


def test_effective_variant_falls_back_to_requested():
    graph = _NoVariant()
    assert cli_run._effective_manifest_variant(graph, "v0") == "v0"


def test_effective_variant_handles_missing_run_settings():
    class _NoSettings:
        pass

    assert cli_run._effective_manifest_variant(_NoSettings(), "v1") == "v1"


# --- manifest wiring uses effective variant ---------------------------------


def test_manifest_writer_uses_effective_variant(tmp_path, monkeypatch):
    captured = {}

    def fake_write_run_manifest(**kwargs):
        captured.update(kwargs)
        return tmp_path / "manifest.json"

    monkeypatch.setattr(cli_run, "write_run_manifest", fake_write_run_manifest)

    class _Stats:
        def get_stats(self):
            return {"llm_calls": 0, "tool_calls": 0, "tokens_in": None, "tokens_out": None}

    selections = {"ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock"}
    graph = _SupportsVariant(workflow_variant="v1")
    variant = cli_run._effective_manifest_variant(graph, "v0")
    write = cli_run._make_manifest_writer(
        {"results_dir": str(tmp_path), "llm_provider": "openai"},
        selections,
        _Stats(),
        variant=variant,
    )
    write(failure=None, outcome="Buy")
    assert captured["variant"] == "v1"
