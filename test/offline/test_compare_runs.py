"""Offline tests for the run-manifest comparison tool (E-owned, D4 / §6.5).

Written test-first. The tool compares v1 run manifests (docs/contracts/run-event.md)
and **refuses** when the runs are not comparable: ticker, trade_date, asset_type,
model (quick/deep tier LLMs), provider (llm_provider + tier providers), language
(output_language), or prompt hashes differ. It reports measured quantities only and
never invents quality scores.

No network; manifests are built via the real recorder and written with ``tmp_path``.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import compare_runs  # noqa: E402
from compare_runs import IncomparableRunsError  # noqa: E402

from tradingagents.run_recorder import RunEvent, write_manifest  # noqa: E402

CONFIG = {
    "llm_provider": "openai",
    "quick_think_llm": "gpt-6-luna",
    "deep_think_llm": "gpt-6-sol",
    "output_language": "English",
}
PROMPT_HASHES = {"market": "sha256:aaa"}

USAGE = {"llm_calls": 10, "tool_calls": 5, "tokens_in": 1000, "tokens_out": 500}


def _event(**overrides) -> RunEvent:
    fields = {
        "run_id": "v2-nvda-2026-11-20-r1-20261121t1200",
        "created_at": "2026-11-21T12:00:00+00:00",
        "version": "0.1.0",
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
        "outcome": "Buy",
        "config_snapshot": dict(CONFIG),
        "prompt_hashes": dict(PROMPT_HASHES),
        "evidence_snapshot": None,
        "usage": dict(USAGE),
        "duration_seconds": 42.5,
        "failure": None,
        "stop_reason": "completed",
    }
    fields.update(overrides)
    return RunEvent(**fields)


def _write(tmp_path, name: str, event: RunEvent) -> Path:
    path = tmp_path / name
    write_manifest(event, path)
    return path


def _manifest(**overrides) -> dict:
    return json.loads(json.dumps(_event(**overrides).__dict__))


# --- Guard: differing key refuses ---------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("ticker", "AMD"),
        ("trade_date", "2026-11-19"),
        ("asset_type", "crypto"),
    ],
)
def test_top_level_guard_mismatch_refuses(field, value):
    baseline = _manifest()
    other = _manifest(**{field: value})
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifests([baseline, other])
    assert field in str(exc.value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("quick_think_llm", "gpt-6-other"),
        ("deep_think_llm", "gpt-6-other"),
        ("llm_provider", "anthropic"),
        ("output_language", "Chinese"),
    ],
)
def test_config_guard_mismatch_refuses(key, value):
    baseline = _manifest()
    other_config = dict(CONFIG)
    other_config[key] = value
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifests([baseline, _manifest(config_snapshot=other_config)])
    assert key in str(exc.value)


def test_prompt_hash_mismatch_refuses():
    baseline = _manifest()
    other = _manifest(prompt_hashes={"market": "sha256:bbb"})
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifests([baseline, other])
    assert "prompt_hashes" in str(exc.value)


def test_missing_model_key_refuses():
    baseline = _manifest()
    no_model = dict(CONFIG)
    del no_model["quick_think_llm"]
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifests([baseline, _manifest(config_snapshot=no_model)])
    assert "quick_think_llm" in str(exc.value)


# --- Positive: comparable runs produce a report ------------------------------


def test_comparable_runs_report_variants():
    a = _manifest(run_id="v0-nvda-2026-11-20-r1-20261121t1200")
    b = _manifest(run_id="v2-nvda-2026-11-20-r1-20261121t1200")
    comparison = compare_runs.compare_manifests([a, b])
    assert [row["run_id"] for row in comparison.variants] == [a["run_id"], b["run_id"]]


def test_single_manifest_is_comparable():
    comparison = compare_runs.compare_manifests([_manifest()])
    assert len(comparison.variants) == 1


def test_empty_input_refuses():
    with pytest.raises(IncomparableRunsError):
        compare_runs.compare_manifests([])


def test_no_quality_score_is_invented():
    comparison = compare_runs.compare_manifests([_manifest(), _manifest()])
    measured = {"variants": comparison.variants, "averages": comparison.averages}
    payload = json.dumps(measured).lower()
    for banned in ("quality", "score", "faithfulness", "relevance"):
        assert banned not in payload
    assert any("no quality score" in note for note in comparison.notes)


# --- Averages per variant ----------------------------------------------------

VARIANT_RUN_1 = _manifest(
    run_id="v2-nvda-2026-11-20-r1-20261121t1200",
    usage={"llm_calls": 10, "tool_calls": 2, "tokens_in": 1000, "tokens_out": 500},
    duration_seconds=40.0,
)
VARIANT_RUN_2 = _manifest(
    run_id="v2-nvda-2026-11-20-r2-20261121t1300",
    usage={"llm_calls": 20, "tool_calls": 4, "tokens_in": 3000, "tokens_out": 1500},
    duration_seconds=60.0,
)


def _variant_of(run_id: str) -> str:
    return run_id.split("-")[0]


def test_averages_per_variant():
    comparison = compare_runs.compare_manifests([VARIANT_RUN_1, VARIANT_RUN_2])
    averages = comparison.averages
    assert set(averages) == {"v2"}
    v2 = averages["v2"]
    assert v2["runs"] == 2
    assert v2["llm_calls"] == pytest.approx(15.0)
    assert v2["tool_calls"] == pytest.approx(3.0)
    assert v2["tokens_in"] == pytest.approx(2000.0)
    assert v2["tokens_out"] == pytest.approx(1000.0)
    assert v2["duration_seconds"] == pytest.approx(50.0)


def test_averages_group_by_variant():
    other = _manifest(
        run_id="v0-nvda-2026-11-20-r1-20261121t1200",
        usage={"llm_calls": 4, "tool_calls": 1, "tokens_in": 100, "tokens_out": 50},
        duration_seconds=10.0,
    )
    comparison = compare_runs.compare_manifests([VARIANT_RUN_1, VARIANT_RUN_2, other])
    assert comparison.averages["v2"]["llm_calls"] == pytest.approx(15.0)
    assert comparison.averages["v0"]["llm_calls"] == pytest.approx(4.0)


def test_average_ignores_null_duration():
    null_dur = _manifest(
        run_id="v2-nvda-2026-11-20-r3-20261121t1400",
        duration_seconds=None,
    )
    v2 = compare_runs.compare_manifests([VARIANT_RUN_1, null_dur]).averages["v2"]
    assert v2["duration_seconds"] == pytest.approx(40.0)


# --- File-level + CLI --------------------------------------------------------


def test_compare_files(tmp_path):
    first = _write(tmp_path, "a.json", _event(run_id="v0-nvda-2026-11-20-r1-20261121t1200"))
    second = _write(tmp_path, "b.json", _event(run_id="v2-nvda-2026-11-20-r1-20261121t1200"))
    comparison = compare_runs.compare_manifest_files([first, second])
    assert len(comparison.variants) == 2


def test_cli_prints_comparison_and_exits_zero(tmp_path, capsys):
    first = _write(tmp_path, "a.json", _event(run_id="v0-nvda-2026-11-20-r1-20261121t1200"))
    second = _write(tmp_path, "b.json", _event(run_id="v2-nvda-2026-11-20-r1-20261121t1200"))
    code = compare_runs.main(["compare_runs.py", str(first), str(second)])
    assert code == 0
    out = capsys.readouterr().out
    assert "v0" in out and "v2" in out


def test_cli_refuses_and_exits_one(tmp_path, capsys):
    first = _write(tmp_path, "a.json", _event())
    second = _write(tmp_path, "b.json", _event(ticker="AMD"))
    code = compare_runs.main(["compare_runs.py", str(first), str(second)])
    assert code == 1
    assert "ticker" in capsys.readouterr().err


def test_cli_usage_error_exits_two(capsys):
    code = compare_runs.main(["compare_runs.py"])
    assert code == 2


# --- Missing token counts are null, shown as -- ------------------------------


def _usage_missing_tokens(**overrides):
    event = _event(**overrides)
    usage = {"llm_calls": 10, "tool_calls": 5}  # token counts absent
    return RunEvent(**{**event.__dict__, "usage": usage})


def test_missing_token_metric_is_null_not_zero():
    event = _usage_missing_tokens(run_id="v0-nvda-2026-11-20-r1-20261121t1200")
    row = compare_runs.compare_manifests([event.__dict__]).variants[0]
    # The reporter must not invent 0 for an unreported token count.
    assert row["tokens_in"] is None
    assert row["tokens_out"] is None


def test_format_metric_shows_dash_for_null():
    assert compare_runs._format_metric(None) == "--"
    assert compare_runs._format_metric(0) == "0"
    assert compare_runs._format_metric(1234) == "1234"


def test_cli_shows_dash_for_missing_tokens(tmp_path, capsys):
    event = _usage_missing_tokens(run_id="v0-nvda-2026-11-20-r1-20261121t1200")
    path = tmp_path / "m.json"
    write_manifest(event, path)
    code = compare_runs.main(["compare_runs.py", str(path)])
    assert code == 0
    out = capsys.readouterr().out
    assert "--" in out


# --- Empty prompt hashes are refused -----------------------------------------


def test_refuse_empty_prompt_hashes():
    event = _event(prompt_hashes={}, run_id="v0-nvda-2026-11-20-r1-20261121t1200")
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifests([event.__dict__])
    assert "prompt_hashes" in str(exc.value)


# --- Outcome / stop_reason counts per variant --------------------------------


def test_outcome_and_stop_reason_counts_per_variant():
    a = _manifest(
        run_id="v2-nvda-2026-11-20-r1-20261121t1200",
        outcome="Buy",
        stop_reason="completed",
    )
    b = _manifest(
        run_id="v2-nvda-2026-11-20-r2-20261121t1300",
        outcome="Buy",
        stop_reason="budget",
    )
    c = _manifest(
        run_id="v2-nvda-2026-11-20-r3-20261121t1400",
        outcome=None,
        stop_reason="completed",
    )
    summary = compare_runs.compare_manifests([a, b, c]).averages["v2"]
    assert summary["outcome_counts"] == {"Buy": 2, "null": 1}
    assert summary["stop_reason_counts"] == {"completed": 2, "budget": 1}


def test_counts_labelled_per_variant():
    v0 = _manifest(run_id="v0-nvda-2026-11-20-r1-20261121t1200", outcome="Hold")
    v2 = _manifest(run_id="v2-nvda-2026-11-20-r1-20261121t1200", outcome="Buy")
    averages = compare_runs.compare_manifests([v0, v2]).averages
    assert averages["v0"]["outcome_counts"] == {"Hold": 1}
    assert averages["v2"]["outcome_counts"] == {"Buy": 1}


# --- Provider keys present in any manifest -----------------------------------


def test_tier_provider_in_non_baseline_manifest_is_compared():
    baseline = _manifest()  # no tier provider keys
    other_config = dict(CONFIG, deep_think_provider="anthropic")
    other = _manifest(config_snapshot=other_config, run_id="v2-nvda-2026-11-20-r2-x")
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifests([baseline, other])
    assert "deep_think_provider" in str(exc.value)


def test_tier_provider_present_in_all_and_matching_passes():
    config = dict(CONFIG, quick_think_provider="openai")
    a = _manifest(config_snapshot=config, run_id="v0-nvda-2026-11-20-r1-x")
    b = _manifest(config_snapshot=dict(config), run_id="v2-nvda-2026-11-20-r1-x")
    comparison = compare_runs.compare_manifests([a, b])
    assert comparison.guard["quick_think_provider"] == "openai"


def test_tier_provider_present_only_in_later_manifest_recorded_in_guard():
    config = dict(CONFIG, quick_think_provider="openai")
    baseline = _manifest()  # omits it -> None
    later = _manifest(config_snapshot=config, run_id="v2-nvda-2026-11-20-r2-x")
    with pytest.raises(IncomparableRunsError):
        compare_runs.compare_manifests([baseline, later])


# --- Bad / missing manifest files --------------------------------------------


def test_missing_file_reports_filename(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifest_files([missing])
    assert "nope.json" in str(exc.value)


def test_bad_json_reports_filename(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifest_files([bad])
    assert "bad.json" in str(exc.value)


def test_unsupported_schema_reports_filename(tmp_path):
    bad = tmp_path / "old.json"
    bad.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
    with pytest.raises(IncomparableRunsError) as exc:
        compare_runs.compare_manifest_files([bad])
    assert "old.json" in str(exc.value)


def test_cli_missing_file_reports_name_no_traceback(tmp_path, capsys):
    missing = tmp_path / "gone.json"
    code = compare_runs.main(["compare_runs.py", str(missing)])
    assert code == 1
    err = capsys.readouterr().err
    assert "gone.json" in err
    assert "Traceback" not in err


def test_cli_bad_json_reports_name_no_traceback(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("<html>", encoding="utf-8")
    code = compare_runs.main(["compare_runs.py", str(bad)])
    assert code == 1
    err = capsys.readouterr().err
    assert "bad.json" in err
    assert "Traceback" not in err
