"""Offline tests for the ``--variant`` option on the analyze command.

The variant selects the architecture under test (v0 original, v1 trimmed, v2
adaptive). It is validated as a safe lowercase slug and threaded through
``run_analysis`` into the run manifest's ``run_id`` instead of the old hardcoded
``v0``. These tests cover the validator, the CLI plumbing, and the manifest.
"""

import pytest
from typer.testing import CliRunner

import cli.main as m
import cli.run as cli_run

# --- validator ---------------------------------------------------------------


def test_variant_accepts_v0_v1_v2():
    for value in ("v0", "v1", "v2"):
        assert cli_run._validate_variant(value) == value


def test_variant_rejects_uppercase():
    with pytest.raises(ValueError):
        cli_run._validate_variant("V2")


def test_variant_rejects_path_traversal():
    with pytest.raises(ValueError):
        cli_run._validate_variant("../x")


def test_variant_rejects_unknown_slug():
    for bad in ("v3", "v", "", "v10", "variant"):
        with pytest.raises(ValueError):
            cli_run._validate_variant(bad)


# --- CLI plumbing ------------------------------------------------------------


def _runner(monkeypatch, calls):
    monkeypatch.setattr(m, "run_analysis", lambda **kw: calls.append(kw))
    calls.clear()
    return CliRunner()


def test_omitted_variant_is_none_legacy(monkeypatch):
    calls = []
    runner = _runner(monkeypatch, calls)
    assert runner.invoke(m.app, []).exit_code == 0
    # Omitted flag = legacy run; None distinguishes it from an explicit v0.
    assert calls[0]["variant"] is None


def test_variant_option_v0_passed_through(monkeypatch):
    calls = []
    runner = _runner(monkeypatch, calls)
    assert runner.invoke(m.app, ["--variant", "v0"]).exit_code == 0
    assert calls[0]["variant"] == "v0"


def test_variant_option_v2_refused_until_workflow_variant(monkeypatch):
    # v2 is valid input but not implemented yet; it is refused before run_analysis.
    calls = []
    runner = _runner(monkeypatch, calls)
    assert runner.invoke(m.app, ["--variant", "v2"]).exit_code != 0
    assert calls == []


def test_invalid_variant_exits_before_running(monkeypatch):
    calls = []
    runner = _runner(monkeypatch, calls)
    result = runner.invoke(m.app, ["--variant", "V2"])
    assert result.exit_code != 0
    assert calls == []


# --- manifest uses the variant ----------------------------------------------


def test_make_manifest_writer_uses_variant(tmp_path, monkeypatch):
    captured = {}

    def fake_write_run_manifest(**kwargs):
        captured.update(kwargs)
        return tmp_path / "manifest.json"

    monkeypatch.setattr(cli_run, "write_run_manifest", fake_write_run_manifest)

    class _Stats:
        def get_stats(self):
            return {"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0}

    selections = {"ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock"}
    config = {"results_dir": str(tmp_path), "llm_provider": "openai"}
    write = cli_run._make_manifest_writer(
        config, selections, _Stats(), started_at=None, variant="v2"
    )
    write(failure=None, outcome="Buy")
    assert captured["variant"] == "v2"


def test_manifest_run_id_reflects_variant(tmp_path):
    path = cli_run.write_run_manifest(
        config={"results_dir": str(tmp_path), "llm_provider": "openai"},
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome="Buy",
        usage={"llm_calls": 1, "tool_calls": 0, "tokens_in": 1, "tokens_out": 0},
        duration_seconds=1.0,
        failure=None,
        variant="v2",
        repeat=1,
        at=cli_run.datetime(2026, 11, 21, 12, 0, tzinfo=cli_run.UTC),
        version="0.7.1",
    )
    assert path.parent.name.startswith("v2-")
