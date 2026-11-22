"""Test standalone preflight against original, temporary checkpoint storage."""

import sqlite3
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from langgraph.checkpoint.base import empty_checkpoint

from tradingagents.graph import checkpointer, trading_graph
from tradingagents.portfolio import PortfolioContext

pytestmark = pytest.mark.unit
TICKER = "NVDA"
DATE = "2026-01-09"
RUN_ID = "original-run"


def _rows(db):
    with closing(sqlite3.connect(db)) as conn:
        return (
            conn.execute("SELECT * FROM checkpoints ORDER BY thread_id").fetchall(),
            conn.execute("SELECT * FROM writes ORDER BY thread_id").fetchall(),
        )


@pytest.fixture
def target(tmp_path):
    inputs = {
        "ticker": TICKER,
        "trade_date": DATE,
        "selected_analysts": ("news", "market"),
        "config": {
            "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 1,
            "quick_think_llm": "original-model",
        },
        "asset_type": "crypto",
        "portfolio": PortfolioContext(cash=100),
        "workflow_variant": "v1",
    }
    keys = (RUN_ID, "neighbor", "")
    ids = {key: trading_graph.checkpoint_thread_id(**inputs, run_key=key) for key in keys}
    with checkpointer.get_checkpointer(tmp_path, TICKER) as saver:
        for key, tid in ids.items():
            saved = saver.put(
                {"configurable": {"thread_id": tid, "checkpoint_ns": ""}},
                empty_checkpoint(),
                {},
                {},
            )
            saver.put_writes(saved, [("marker", key)], "task")
    default_path = tmp_path / "checkpoints" / f"{TICKER}.db"
    db = default_path.rename(tmp_path / "original # checkpoint.db")
    assert tuple(map(len, _rows(db))) == (3, 3)
    return SimpleNamespace(db=db, ids=ids, inputs=inputs)


def _preflight(target, **overrides):
    kwargs = {
        "db": target.db,
        "recorded_thread_id": target.ids[RUN_ID],
        "run_id": RUN_ID,
        **target.inputs,
        **overrides,
    }
    return trading_graph.preflight_checkpoint_resume(**kwargs)


def test_preflight_verifies_exact_original_target(target, monkeypatch):
    """Provisional: REQ-C-LOCAL-CKPT-006 and INV-C-LOCAL-CKPT-006."""
    before = _rows(target.db)
    lookup = Mock(wraps=checkpointer.checkpoint_thread_exists)
    monkeypatch.setattr(trading_graph, "checkpoint_thread_exists", lookup, raising=False)

    assert _preflight(target) == target.ids[RUN_ID]

    lookup.assert_called_once_with(target.db, target.ids[RUN_ID])
    assert _rows(target.db) == before


@pytest.mark.parametrize("change", ["model", "variant"])
def test_preflight_mismatch_never_reads_storage(target, monkeypatch, change):
    """Provisional: REQ-C-LOCAL-CKPT-006 and INV-C-LOCAL-CKPT-006."""
    before = _rows(target.db)
    lookup = Mock(side_effect=AssertionError("mismatch must not read storage"))
    monkeypatch.setattr(trading_graph, "checkpoint_thread_exists", lookup, raising=False)
    # Legacy at the same debate depth still differs from explicit v1.
    overrides = (
        {"config": {**target.inputs["config"], "quick_think_llm": "changed-model"}}
        if change == "model"
        else {"workflow_variant": None}
    )

    with pytest.raises(trading_graph.CheckpointResumePreflightError) as error:
        _preflight(target, **overrides)

    assert error.value.code == "checkpoint_signature_mismatch"
    lookup.assert_not_called()
    assert _rows(target.db) == before


def test_preflight_empty_run_id_cannot_select_legacy_thread(target, monkeypatch):
    """Provisional: INV-C-LOCAL-CKPT-006."""
    lookup = Mock(side_effect=AssertionError("empty run ID must not read storage"))
    monkeypatch.setattr(trading_graph, "checkpoint_thread_exists", lookup, raising=False)

    with pytest.raises(trading_graph.CheckpointResumePreflightError) as error:
        _preflight(target, run_id="", recorded_thread_id=target.ids[""])

    assert error.value.code == "checkpoint_invalid_run_id"
    lookup.assert_not_called()


def test_preflight_missing_db_does_not_search_other_databases(target, tmp_path):
    """Provisional: REQ-C-LOCAL-CKPT-006 and INV-C-LOCAL-CKPT-006."""
    before = _rows(target.db)
    missing_db = tmp_path / "absent" / "original.db"
    with pytest.raises(trading_graph.CheckpointResumePreflightError) as error:
        _preflight(target, db=missing_db)

    assert error.value.code == "checkpoint_not_found"
    assert not missing_db.parent.exists()
    assert _rows(target.db) == before


def test_preflight_missing_thread_does_not_use_neighbors(target):
    """Provisional: REQ-C-LOCAL-CKPT-006 and INV-C-LOCAL-CKPT-006."""
    before = _rows(target.db)
    missing_run_id = "absent-run"
    missing_thread = trading_graph.checkpoint_thread_id(**target.inputs, run_key=missing_run_id)

    with pytest.raises(trading_graph.CheckpointResumePreflightError) as error:
        _preflight(target, run_id=missing_run_id, recorded_thread_id=missing_thread)

    assert error.value.code == "checkpoint_not_found"
    assert _rows(target.db) == before


def test_preflight_preserves_storage_errors(target, tmp_path):
    """Provisional: INV-C-LOCAL-CKPT-006."""
    corrupt_db = tmp_path / "corrupt.db"
    payload = b"not a SQLite database"
    corrupt_db.write_bytes(payload)
    with pytest.raises(sqlite3.DatabaseError, match="file is not a database"):
        _preflight(target, db=corrupt_db)

    assert corrupt_db.read_bytes() == payload
