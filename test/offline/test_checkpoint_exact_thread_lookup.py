"""Offline checks for read-only lookup of an original checkpoint thread."""

import sqlite3
from contextlib import closing

import pytest
from langgraph.checkpoint.base import empty_checkpoint

from tradingagents.graph import checkpointer

pytestmark = pytest.mark.unit
THREAD_ARGS = ("NVDA", "2026-01-09", "sig-a")


@pytest.fixture
def storage(tmp_path):
    ids = {key: checkpointer.thread_id(*THREAD_ARGS, run_key=key) for key in ("", "r1", "r2")}
    with checkpointer.get_checkpointer(tmp_path, THREAD_ARGS[0]) as saver:
        for key, metadata in (("", {"step": 3}), ("r1", {}), ("r2", {"step": 11})):
            config = {"configurable": {"thread_id": ids[key], "checkpoint_ns": ""}}
            saved = saver.put(config, empty_checkpoint(), metadata, {})
            saver.put_writes(saved, [("marker", key)], "task")
        saved = saver.get_tuple({"configurable": {"thread_id": ids["r1"]}})
        assert saved is not None
        assert "step" not in saved.metadata
    return tmp_path / "checkpoints" / "NVDA.db", ids


def _rows(db):
    with closing(sqlite3.connect(db)) as conn:
        return {
            "checkpoints": conn.execute("SELECT * FROM checkpoints ORDER BY thread_id").fetchall(),
            "writes": conn.execute("SELECT * FROM writes ORDER BY thread_id").fetchall(),
        }


def test_exact_original_threads_exist_without_step_metadata(storage):
    """Provisional: REQ-C-LOCAL-CKPT-005 and INV-C-LOCAL-CKPT-005."""
    db, ids = storage
    before = _rows(db)
    assert all(len(rows) == 3 for rows in before.values())
    for tid in ids.values():
        assert checkpointer.checkpoint_thread_exists(db, tid) is True
    assert _rows(db) == before


def test_missing_thread_does_not_use_nearby_threads(storage):
    """Provisional: REQ-C-LOCAL-CKPT-005 and INV-C-LOCAL-CKPT-005."""
    db, ids = storage
    before = _rows(db)
    assert checkpointer.checkpoint_thread_exists(db, ids["r1"] + "0") is False
    assert checkpointer.checkpoint_thread_exists(db, "' OR 1=1 --") is False
    assert _rows(db) == before


def test_missing_database_does_not_create_parent(tmp_path):
    """Provisional: INV-C-LOCAL-CKPT-005."""
    db = tmp_path / "absent" / "NVDA.db"
    assert checkpointer.checkpoint_thread_exists(db, "missing") is False
    assert not db.parent.exists()


def test_database_path_with_spaces_and_hash(storage):
    """Provisional: REQ-C-LOCAL-CKPT-005."""
    db, ids = storage
    original = db.rename(db.with_name("original # run.db"))
    assert checkpointer.checkpoint_thread_exists(str(original), ids["r1"]) is True
    assert not db.exists()


@pytest.mark.parametrize("kind", ["corrupt", "missing-table"])
def test_storage_errors_are_not_reported_as_absence(tmp_path, kind):
    """Provisional: INV-C-LOCAL-CKPT-005."""
    db = tmp_path / "invalid.db"
    if kind == "corrupt":
        db.write_bytes(b"This is not SQLite.")
        message = "file is not a database"
    else:
        with closing(sqlite3.connect(db)) as conn:
            conn.execute("CREATE TABLE unrelated (thread_id TEXT)")
        message = "no such table: checkpoints"
    before = db.read_bytes()

    with pytest.raises(sqlite3.DatabaseError, match=message):
        checkpointer.checkpoint_thread_exists(db, "missing")

    assert db.read_bytes() == before
