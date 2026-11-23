"""Exercise run-scoped lookup and cleanup in one real SQLite database."""

import sqlite3
from contextlib import closing

import pytest
from langgraph.checkpoint.base import empty_checkpoint

from tradingagents.graph.checkpointer import (
    checkpoint_step,
    clear_checkpoint,
    get_checkpointer,
    thread_id,
)

pytestmark = pytest.mark.unit

TICKER = "NVDA"
DATE = "2026-01-09"
SIGNATURE = "sig-a"
STEPS = {"": 3, "r1": 7, "r2": 11}
THREAD_ARGS = (TICKER, DATE, SIGNATURE)


def _thread_rows(db):
    """Read both tables directly so a lookup result cannot hide leftover writes."""
    with closing(sqlite3.connect(db)) as conn:
        return {
            "checkpoints": dict(conn.execute("SELECT thread_id, COUNT(*) FROM checkpoints GROUP BY thread_id")),
            "writes": dict(conn.execute("SELECT thread_id, COUNT(*) FROM writes GROUP BY thread_id")),
        }


@pytest.fixture
def storage(tmp_path):
    ids = {key: thread_id(*THREAD_ARGS, run_key=key) for key in STEPS}
    assert len(set(ids.values())) == 3
    with get_checkpointer(tmp_path, TICKER) as saver:
        for key, step in STEPS.items():
            config = {"configurable": {"thread_id": ids[key], "checkpoint_ns": ""}}
            saved = saver.put(config, empty_checkpoint(), {"step": step}, {})
            saver.put_writes(saved, [("marker", step)], "task")

        for key, step in STEPS.items():
            saved = saver.get_tuple({"configurable": {"thread_id": ids[key]}})
            assert saved is not None
            assert saved.metadata["step"] == step

    db = tmp_path / "checkpoints" / f"{TICKER}.db"
    assert db.is_file()
    expected = dict.fromkeys(ids.values(), 1)
    assert _thread_rows(db) == {"checkpoints": expected, "writes": expected}
    return tmp_path, db, ids


def test_keyed_lookup_returns_only_the_requested_step(storage):
    """Provisional: REQ-C-LOCAL-CKPT-003."""
    data_dir, _, _ = storage
    assert checkpoint_step(data_dir, *THREAD_ARGS, run_key="r1") == STEPS["r1"]
    assert checkpoint_step(data_dir, *THREAD_ARGS, run_key="r2") == STEPS["r2"]
    assert checkpoint_step(data_dir, *THREAD_ARGS, run_key="") == STEPS[""]


def test_unknown_key_does_not_fall_back_or_delete_existing_threads(storage):
    """Provisional: REQ-C-LOCAL-CKPT-003 and INV-C-LOCAL-CKPT-003."""
    data_dir, db, _ = storage
    before = _thread_rows(db)
    assert checkpoint_step(data_dir, *THREAD_ARGS, run_key="missing") is None
    clear_checkpoint(data_dir, *THREAD_ARGS, run_key="missing")
    assert _thread_rows(db) == before
    assert checkpoint_step(data_dir, *THREAD_ARGS) == STEPS[""]
    for key in ("r1", "r2"):
        assert checkpoint_step(data_dir, *THREAD_ARGS, run_key=key) == STEPS[key]


def test_keyed_cleanup_removes_only_target_checkpoint_and_writes(storage):
    """Provisional: INV-C-LOCAL-CKPT-003."""
    data_dir, db, ids = storage
    clear_checkpoint(data_dir, *THREAD_ARGS, run_key="r1")
    remaining = dict.fromkeys((ids[""], ids["r2"]), 1)
    assert _thread_rows(db) == {"checkpoints": remaining, "writes": remaining}
    assert checkpoint_step(data_dir, *THREAD_ARGS, run_key="r1") is None
    assert checkpoint_step(data_dir, *THREAD_ARGS, run_key="r2") == STEPS["r2"]
    assert checkpoint_step(data_dir, *THREAD_ARGS) == STEPS[""]


def test_unkeyed_lookup_and_cleanup_still_target_legacy_thread(storage):
    """Provisional: INV-C-LOCAL-CKPT-003."""
    data_dir, db, ids = storage
    assert checkpoint_step(data_dir, *THREAD_ARGS) == STEPS[""]
    clear_checkpoint(data_dir, *THREAD_ARGS)
    assert checkpoint_step(data_dir, *THREAD_ARGS) is None
    remaining = dict.fromkeys((ids["r1"], ids["r2"]), 1)
    assert _thread_rows(db) == {"checkpoints": remaining, "writes": remaining}
