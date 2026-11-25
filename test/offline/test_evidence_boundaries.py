"""Offline tests for C's closeout-review boundary fixes (E side).

Three concerns from ``C-to-E-evidence-interface-closeout-review.md``:

1. **Capture opt-in** (default OFF, independent of run id and evidence mode).
   A real ``--capture-evidence`` flag threads into ``run_analysis``; the capture
   context reaches ``create_run_state`` only when the flag is on, still behind the
   ``source_run_id`` introspection guard. Capture with checkpointing enabled fails
   before graph construction, model calls, reservation or destination prep.
2. **Containment.** ``evidence_destination`` anchors to the intended reserved run
   directory first, validates ``run_id`` against ``RUN_ID_PATTERN`` (rejecting
   dot-only ids), and rejects symlinks along the root chain that escape the
   intended tree *before* creating any directory.
3. **Failure acceptance.** A post-reservation failure during initial state
   construction still writes a failure manifest using the same reservation and
   preserves the original error. A sidecar failure after the manifest is already
   published must NOT trigger a second ``write_manifest``; the original error is
   preserved and cleanup does not run.

No model, no network, no ``.env``.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import cli.run as cli_run  # noqa: E402
from tradingagents import evidence_store  # noqa: E402
from tradingagents.run_recorder import read_manifest  # noqa: E402

FIXED_AT = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
DIGEST = "0123456789abcdef" * 4
ARTIFACT_KEY = "v1/" + DIGEST + ".json"


def _config(tmp_path, **overrides):
    config = {
        "results_dir": str(tmp_path),
        "llm_provider": "openai",
        "quick_think_llm": "gpt-6-luna",
        "deep_think_llm": "gpt-6-sol",
        "output_language": "English",
    }
    config.update(overrides)
    return config


# =============================================================================
# 1. Capture opt-in
# =============================================================================


def _supports(**_kwargs):
    pass


def test_capture_default_is_off(monkeypatch):
    """run_analysis default must not request capture (signature default False)."""
    import inspect

    params = inspect.signature(cli_run.run_analysis).parameters
    assert "capture_evidence" in params
    assert params["capture_evidence"].default is False


def _capture_kwargs_seen():
    """A fake create_run_state that records the kwargs it is called with."""
    seen = {}

    class _Graph:
        def create_run_state(self, company, trade_date, asset_type="stock",
                             portfolio=None, *, source_run_id=None,
                             capture_context=None):
            seen["source_run_id"] = source_run_id
            seen["capture_context"] = capture_context
            return {}

    return _Graph(), seen


def test_capture_off_does_not_pass_capture_context():
    graph, seen = _capture_kwargs_seen()
    cli_run._create_run_state(
        graph, "NVDA", "2026-11-20", "stock", None, "reserved-id",
        capture_evidence=False, capture_context={"enabled": True},
    )
    # Default-off: source_run_id still forwarded, but capture_context stays None.
    assert seen["source_run_id"] == "reserved-id"
    assert seen["capture_context"] is None


def test_capture_on_passes_capture_context():
    graph, seen = _capture_kwargs_seen()
    cli_run._create_run_state(
        graph, "NVDA", "2026-11-20", "stock", None, "reserved-id",
        capture_evidence=True, capture_context={"enabled": True},
    )
    assert seen["source_run_id"] == "reserved-id"
    assert seen["capture_context"] == {"enabled": True}


def test_capture_on_without_capture_param_fails_closed():
    """Capture requested but graph's create_run_state cannot accept it -> raise."""

    class _LegacyGraph:
        def create_run_state(self, company, trade_date, asset_type="stock",
                             portfolio=None, *, source_run_id=None):
            return {}

    with pytest.raises(ValueError):
        cli_run._create_run_state(
            _LegacyGraph(), "NVDA", "2026-11-20", "stock", None, "reserved-id",
            capture_evidence=True, capture_context={"enabled": True},
        )


def test_capture_with_checkpoint_fails_before_any_work(monkeypatch, tmp_path):
    """capture + checkpoint enabled must refuse before graph/reservation/model."""
    called = {"graph": False, "reserve": False}

    def _boom_graph(*a, **k):
        called["graph"] = True
        raise AssertionError("graph must not be built")

    def _boom_reserve(*a, **k):
        called["reserve"] = True
        raise AssertionError("reservation must not happen")

    monkeypatch.setattr(cli_run, "TradingAgentsGraph", _boom_graph)
    monkeypatch.setattr(cli_run, "_build_graph", _boom_graph)
    monkeypatch.setattr(cli_run, "reserve_run_id", _boom_reserve)
    # Selections can be stubbed so the refusal is the only thing that can fire.
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags: {
        "ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock",
        "analysts": [], "research_depth": 1, "quick_think_llm": "q",
        "deep_think_llm": "d", "backend_url": None, "llm_provider": "openai",
        "output_language": "English",
    })

    import cli.run as cr
    with pytest.raises((ValueError, SystemExit)) as exc:
        cr.run_analysis(checkpoint=True, flags={}, capture_evidence=True)
    assert not called["graph"]
    assert not called["reserve"]
    # No run directory was prepared.
    assert not (tmp_path / "runs").exists() or not any((tmp_path / "runs").iterdir())
    _ = exc


# =============================================================================
# 2. Containment
# =============================================================================


def test_canonical_key_ok(tmp_path):
    dest = evidence_store.evidence_destination(_config(tmp_path), "v0-nvda-2026-11-20-r1-x", ARTIFACT_KEY)
    assert dest.parent.is_dir()
    assert dest.name == DIGEST + ".json"


@pytest.mark.parametrize("bad_run_id", [
    "..", ".", "a/b", "a\\b", "V0-upper", "", "-leading", "with space",
], ids=["dotdot", "dot", "slash", "backslash", "uppercase", "empty", "leading-dash", "space"])
def test_noncanonical_run_id_rejected(tmp_path, bad_run_id):
    with pytest.raises(ValueError):
        evidence_store.evidence_destination(_config(tmp_path), bad_run_id, ARTIFACT_KEY)


def test_symlinked_evidence_dir_escape_rejected_before_creation(tmp_path):
    run_id = "v0-nvda-2026-11-20-r1-x"
    run_root = tmp_path / "runs" / run_id
    run_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    # evidence is a symlink pointing outside the run.
    (run_root / "evidence").symlink_to(outside, target_is_directory=True)
    before = set((tmp_path / "runs").rglob("*"))
    with pytest.raises(ValueError):
        evidence_store.evidence_destination(_config(tmp_path), run_id, ARTIFACT_KEY)
    after = set((tmp_path / "runs").rglob("*"))
    assert before == after  # nothing created


def test_symlinked_parent_run_escape_rejected(tmp_path):
    run_id = "v0-nvda-2026-11-20-r1-x"
    outside = tmp_path / "outside"
    outside.mkdir()
    runs = tmp_path / "runs"
    runs.mkdir()
    # runs/<run_id> is a symlink pointing outside results_dir.
    (runs / run_id).symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        evidence_store.evidence_destination(_config(tmp_path), run_id, ARTIFACT_KEY)


# =============================================================================
# 3. Failure acceptance
# =============================================================================


class _Stats:
    def get_stats(self):
        return {"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0}


def _selections():
    return {"ticker": "NVDA", "analysis_date": "2026-11-20", "asset_type": "stock"}


def test_init_failure_after_reservation_writes_one_failure_manifest(tmp_path):
    """A create_run_state failure routes to a failure manifest on the same id."""
    run_id = cli_run.reserve_run_id(
        config=_config(tmp_path), variant="v0", ticker="NVDA",
        trade_date="2026-11-20", repeat=1, at=FIXED_AT,
    )

    class _Graph:
        def create_run_state(self, *a, **k):
            raise RuntimeError("init boom")

    graph = _Graph()
    write = cli_run._make_manifest_writer(
        _config(tmp_path), _selections(), _Stats(), started_at=0.0,
        variant="v0", run_id=run_id,
    )
    # Simulate run_analysis wrapping init inside the finalize try/except.
    with pytest.raises(RuntimeError, match="init boom"):
        try:
            cli_run._create_run_state(graph, "NVDA", "2026-11-20", "stock", None, run_id,
                                      capture_evidence=False, capture_context=None)
        except BaseException as failure:
            cli_run._finalize_run_manifest(
                write=write, graph=graph, ticker="NVDA", trade_date="2026-11-20",
                asset_type="stock", portfolio=None, final_state=None, failure=failure,
            )
    manifests = list((tmp_path / "runs" / run_id).glob("manifest.json"))
    assert len(manifests) == 1
    assert read_manifest(manifests[0])["failure"] == "init boom"
    assert not (tmp_path / "runs" / f"{run_id}-2").exists()


def test_sidecar_failure_after_publish_no_second_write(tmp_path, monkeypatch):
    """A sidecar failure after write_manifest must not cause a second write."""
    run_id = cli_run.reserve_run_id(
        config=_config(tmp_path), variant="v0", ticker="NVDA",
        trade_date="2026-11-20", repeat=1, at=FIXED_AT,
    )

    write_calls = {"n": 0}
    real_write_manifest = cli_run.write_manifest

    def _counting_write_manifest(event, path):
        write_calls["n"] += 1
        return real_write_manifest(event, path)

    monkeypatch.setattr(cli_run, "write_manifest", _counting_write_manifest)

    def _boom_sidecar(*a, **k):
        raise OSError("sidecar boom")

    monkeypatch.setattr(cli_run, "write_evidence_mode", _boom_sidecar)

    with pytest.raises(cli_run.SidecarError) as exc:
        cli_run.write_run_manifest(
            config=_config(tmp_path), ticker="NVDA", trade_date="2026-11-20",
            asset_type="stock", outcome="Buy",
            usage={"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0},
            duration_seconds=1.0, failure=None, variant="v0", repeat=1,
            at=FIXED_AT, version="0.7.1", run_id=run_id,
        )
    # Exactly one terminal manifest write, and "sidecar boom" is the visible cause.
    assert write_calls["n"] == 1
    assert "sidecar boom" in str(exc.value)
    manifest_path = tmp_path / "runs" / run_id / "manifest.json"
    assert manifest_path.is_file()  # not overwritten / not removed
    # A sidecar-error marker records the failure explicitly.
    marker = tmp_path / "runs" / run_id / "sidecar-error.json"
    assert marker.is_file()


def test_sidecar_failure_after_publish_no_cleanup(tmp_path, monkeypatch):
    """Cleanup (record_decision/clear_checkpoint) must not run when sidecar fails."""
    run_id = cli_run.reserve_run_id(
        config=_config(tmp_path), variant="v0", ticker="NVDA",
        trade_date="2026-11-20", repeat=1, at=FIXED_AT,
    )

    class _Graph:
        def __init__(self):
            self.recorded = False
            self.cleared = False

        def record_decision(self, *a, **k):
            self.recorded = True

        def clear_checkpoint_on_success(self, *a, **k):
            self.cleared = True

    def _boom_sidecar(*a, **k):
        raise OSError("sidecar boom")

    monkeypatch.setattr(cli_run, "write_evidence_mode", _boom_sidecar)

    graph = _Graph()
    write = cli_run._make_manifest_writer(
        _config(tmp_path), _selections(), _Stats(), started_at=0.0,
        variant="v0", run_id=run_id,
    )
    with pytest.raises(cli_run.SidecarError):
        cli_run._finalize_run_manifest(
            write=write, graph=graph, ticker="NVDA", trade_date="2026-11-20",
            asset_type="stock", portfolio=None,
            final_state={"final_rating": "Buy"}, failure=None,
        )
    assert graph.recorded is False
    assert graph.cleared is False


# =============================================================================
# 4. CLI flag wiring
# =============================================================================


def test_cli_exposes_capture_evidence_option():
    """main.analyze exposes a real --capture-evidence option, default False."""
    import typer

    import cli.main as cli_main

    params = typer.main.get_command(cli_main.app).params
    opt = next((p for p in params if p.name == "capture_evidence"), None)
    assert opt is not None
    assert any("--capture-evidence" in o for o in opt.opts)
    assert opt.default is False
