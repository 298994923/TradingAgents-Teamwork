"""Offline tests for wiring B's ``on_prompt`` receipts into the run manifest.

The graph/producer side (``agents/prompt_receipts.py``) emits one receipt per
model send, tagging the static-template digest under the key ``b.<role>``. The
manifest contract (``docs/contracts/run-event.md`` field 10) wants plain role
keys ``bull`` / ``bear`` / ``research_manager``. The CLI is the sole manifest
writer, so it collects the receipts, normalizes ``b.<role>`` -> ``<role>`` (same
digest, relabelled key), keeps the raw receipts in a sidecar for audit, and
refuses to write a manifest when a required role is missing, a hash is empty, or
a role's hashes disagree.

Contract refs: ``docs/contracts/run-event.md`` field 10; ``docs/evaluation/protocol.md``
(``prompt_hashes`` is a guard, empty refused); ``docs/handoffs/E-to-B-prompt_hashes-接入说明.md``.
Invariant (comparison gate): the three roles ``bull`` / ``bear`` / ``research_manager``
must be present and non-empty; malformed input fails closed (refuse, never guess).

No network, no model: receipts are synthetic; manifests are written to ``tmp_path``.
"""

import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import compare_runs  # noqa: E402

import cli.run as cli_run  # noqa: E402
from tradingagents.run_recorder import RunEvent, read_manifest  # noqa: E402

FIXED_AT = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)

REQUIRED_ROLES = ("bull", "bear", "research_manager")

# Static-template digests, one per role (distinct, non-empty).
TEMPLATE_DIGESTS = {
    "bull": "a" * 64,
    "bear": "b" * 64,
    "research_manager": "c" * 64,
}


def _receipt(role, digest=None, *, round_index=0, run_id="v0-nvda-2026-11-20-r1-x"):
    """A receipt shaped exactly like ``legacy_prompt_observer`` emits it."""
    digest = TEMPLATE_DIGESTS[role] if digest is None else digest
    return {
        "role": role,
        "run_id": run_id,
        "round_index": round_index,
        "prompt_hashes": {"b." + role: digest},
        "input_sha256": "0" * 64,
    }


def _v0_receipts():
    """v0-shaped stream: two debate rounds + one manager."""
    return [
        _receipt("bull", round_index=0),
        _receipt("bear", round_index=0),
        _receipt("bull", round_index=1),
        _receipt("bear", round_index=1),
        _receipt("research_manager"),
    ]


def _v1_receipts():
    """v1-shaped stream: one debate round + one manager."""
    return [
        _receipt("bull", round_index=0),
        _receipt("bear", round_index=0),
        _receipt("research_manager"),
    ]


def _config(**overrides) -> dict:
    config = {
        "results_dir": "/tmp/results",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-6-luna",
        "deep_think_llm": "gpt-6-sol",
        "output_language": "English",
    }
    config.update(overrides)
    return config


def _write(config=None, **overrides):
    """Call ``write_run_manifest`` with sensible defaults; return the path."""
    kwargs = {
        "config": config or _config(),
        "ticker": "NVDA",
        "trade_date": "2026-11-20",
        "asset_type": "stock",
        "outcome": "Buy",
        "usage": {"llm_calls": 5, "tool_calls": 0, "tokens_in": 10, "tokens_out": 5},
        "duration_seconds": 1.0,
        "failure": None,
        "variant": "v0",
        "repeat": 1,
        "at": FIXED_AT,
        "version": "0.7.1",
    }
    kwargs.update(overrides)
    return cli_run.write_run_manifest(**kwargs)


# --- collector: normalization + validation -----------------------------------


def test_collector_normalizes_b_prefixed_keys_to_plain_roles():
    collector = cli_run._collect_prompt_receipts()
    for receipt in _v0_receipts():
        collector.sink(receipt)
    assert collector.prompt_hashes() == dict(TEMPLATE_DIGESTS)


def test_collector_keeps_raw_receipts_with_b_prefix():
    receipts = _v0_receipts()
    collector = cli_run._collect_prompt_receipts()
    for receipt in receipts:
        collector.sink(receipt)
    raw = collector.raw_receipts()
    assert raw == receipts
    # Raw receipts keep B's original "b.<role>" key for audit.
    assert all(list(r["prompt_hashes"]) == ["b." + r["role"]] for r in raw)


def test_collector_accepts_v1_single_round():
    collector = cli_run._collect_prompt_receipts()
    for receipt in _v1_receipts():
        collector.sink(receipt)
    assert collector.prompt_hashes() == dict(TEMPLATE_DIGESTS)


def test_collector_zero_receipts_returns_empty():
    # A legacy or fake-graph run never calls the sink: no receipts must default
    # to an empty dict (old behavior), not fail the manifest write.
    collector = cli_run._collect_prompt_receipts()
    assert collector.prompt_hashes() == {}


def test_collector_rejects_missing_role():
    collector = cli_run._collect_prompt_receipts()
    for receipt in (_receipt("bull"), _receipt("bear")):
        collector.sink(receipt)
    with pytest.raises(ValueError, match="research_manager"):
        collector.prompt_hashes()


def test_collector_rejects_empty_hash():
    collector = cli_run._collect_prompt_receipts()
    collector.sink(_receipt("bull", digest=""))
    collector.sink(_receipt("bear"))
    collector.sink(_receipt("research_manager"))
    with pytest.raises(ValueError):
        collector.prompt_hashes()


def test_collector_rejects_none_hash():
    collector = cli_run._collect_prompt_receipts()
    collector.sink(_receipt("bull", digest=None) | {"prompt_hashes": {"b.bull": None}})
    collector.sink(_receipt("bear"))
    collector.sink(_receipt("research_manager"))
    with pytest.raises(ValueError):
        collector.prompt_hashes()


def test_collector_rejects_disagreeing_hashes_for_same_role():
    collector = cli_run._collect_prompt_receipts()
    collector.sink(_receipt("bull", round_index=0, digest="a" * 64))
    collector.sink(_receipt("bull", round_index=1, digest="d" * 64))
    collector.sink(_receipt("bear"))
    collector.sink(_receipt("research_manager"))
    with pytest.raises(ValueError, match="bull"):
        collector.prompt_hashes()


def test_collector_repeated_identical_hashes_are_fine():
    # The same template across two rounds is the normal case: identical digests
    # for one role must NOT be treated as a disagreement.
    collector = cli_run._collect_prompt_receipts()
    for receipt in _v0_receipts():
        collector.sink(receipt)
    assert collector.prompt_hashes()["bull"] == TEMPLATE_DIGESTS["bull"]


# --- write_run_manifest: manifest + sidecar ----------------------------------


def test_normal_run_writes_three_hashes_into_manifest(tmp_path):
    collector = cli_run._collect_prompt_receipts()
    for receipt in _v0_receipts():
        collector.sink(receipt)
    path = _write(
        config=_config(results_dir=str(tmp_path)),
        prompt_hashes=collector.prompt_hashes(),
        prompt_receipts=collector.raw_receipts(),
    )
    manifest = read_manifest(path)
    assert set(manifest["prompt_hashes"]) == set(REQUIRED_ROLES)
    assert all(manifest["prompt_hashes"][role] for role in REQUIRED_ROLES)
    assert manifest["prompt_hashes"] == dict(TEMPLATE_DIGESTS)


def test_normal_run_writes_raw_receipts_sidecar(tmp_path):
    collector = cli_run._collect_prompt_receipts()
    for receipt in _v0_receipts():
        collector.sink(receipt)
    path = _write(
        config=_config(results_dir=str(tmp_path)),
        prompt_hashes=collector.prompt_hashes(),
        prompt_receipts=collector.raw_receipts(),
    )
    sidecar = path.parent / "prompt-receipts.jsonl"
    assert sidecar.exists()
    lines = [json.loads(line) for line in sidecar.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == len(_v0_receipts())
    assert all(list(row["prompt_hashes"]) == ["b." + row["role"]] for row in lines)


def test_zero_receipts_writes_manifest_with_empty_hashes(tmp_path):
    # A legacy / fake-graph run collects nothing; the manifest must still be
    # written with prompt_hashes == {} and no sidecar (compare_runs refuses it).
    collector = cli_run._collect_prompt_receipts()
    path = _write(
        config=_config(results_dir=str(tmp_path)),
        prompt_hashes=collector.prompt_hashes(),
        prompt_receipts=collector.raw_receipts(),
    )
    manifest = read_manifest(path)
    assert manifest["prompt_hashes"] == {}
    assert not (path.parent / "prompt-receipts.jsonl").exists()


def test_missing_role_receipts_never_reach_manifest(tmp_path):
    # Finalize refuses: no manifest is written when a required role is absent.
    collector = cli_run._collect_prompt_receipts()
    for receipt in (_receipt("bull"), _receipt("bear")):
        collector.sink(receipt)
    with pytest.raises(ValueError, match="research_manager"):
        hashes = collector.prompt_hashes()
        _write(
            config=_config(results_dir=str(tmp_path)),
            prompt_hashes=hashes,
            prompt_receipts=collector.raw_receipts(),
        )
    assert not (tmp_path / "runs").exists()


# --- done criterion: v0 and v1 manifests are comparable ----------------------


def _run_event(run_id: str, prompt_hashes: dict) -> dict:
    """A manifest dict (as ``compare_manifests`` consumes it) for one run."""
    event = RunEvent(
        run_id=run_id,
        created_at="2026-11-21T12:00:00+00:00",
        version="0.7.1",
        ticker="NVDA",
        trade_date="2026-11-20",
        asset_type="stock",
        outcome="Buy",
        config_snapshot=dict(_config()),
        prompt_hashes=prompt_hashes,
        evidence_snapshot=None,
        usage={"llm_calls": 5, "tool_calls": 0, "tokens_in": 10, "tokens_out": 5},
        duration_seconds=1.0,
        failure=None,
        stop_reason="completed",
    )
    return asdict(event)


def test_v0_and_v1_manifests_are_comparable(tmp_path):
    v0_collector = cli_run._collect_prompt_receipts()
    for receipt in _v0_receipts():
        v0_collector.sink(receipt)
    v1_collector = cli_run._collect_prompt_receipts()
    for receipt in _v1_receipts():
        v1_collector.sink(receipt)

    v0_hashes = v0_collector.prompt_hashes()
    v1_hashes = v1_collector.prompt_hashes()
    # Same static templates -> identical guards across variants.
    assert v0_hashes == v1_hashes == dict(TEMPLATE_DIGESTS)

    v0_manifest = _run_event("v0-nvda-2026-11-20-r1-20261121t1200", v0_hashes)
    v1_manifest = _run_event("v1-nvda-2026-11-20-r1-20261121t1300", v1_hashes)
    # compare_runs accepts the pair (does not raise IncomparableRunsError).
    comparison = compare_runs.compare_manifests([v0_manifest, v1_manifest])
    assert comparison.guard["prompt_hashes"] == dict(TEMPLATE_DIGESTS)
    assert {row["variant"] for row in comparison.variants} == {"v0", "v1"}


def test_manifest_written_and_readable_via_recorder(tmp_path):
    # End-to-end through the real recorder: the three hashes survive on disk.
    collector = cli_run._collect_prompt_receipts()
    for receipt in _v1_receipts():
        collector.sink(receipt)
    path = _write(
        config=_config(results_dir=str(tmp_path)),
        variant="v1",
        prompt_hashes=collector.prompt_hashes(),
        prompt_receipts=collector.raw_receipts(),
    )
    manifest = read_manifest(path)
    assert path.parent.name.startswith("v1-")
    assert manifest["prompt_hashes"] == dict(TEMPLATE_DIGESTS)
