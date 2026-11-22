"""Verify exact-thread cleanup against temporary SQLite checkpoint storage."""

import sqlite3
from contextlib import closing

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

from tradingagents.graph import checkpointer

pytestmark = pytest.mark.unit
TABLES = ("writes", "checkpoints")
IDENTITY = ("NVDA", "2026-01-09", "sig-a")
ORIGINAL = checkpointer.thread_id(*IDENTITY, run_key="original")
NEIGHBOR = checkpointer.thread_id(*IDENTITY, run_key="neighbor")
LEGACY = checkpointer.thread_id(*IDENTITY)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "original run #1.db"
    with closing(sqlite3.connect(path)) as conn:
        SqliteSaver(conn).setup()
        with conn:
            for tid in (ORIGINAL, NEIGHBOR, LEGACY):
                for checkpoint in ("step-1", "step-2"):
                    conn.execute(
                        "INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)",
                        (tid, checkpoint),
                    )
                    conn.execute(
                        "INSERT INTO writes (thread_id, checkpoint_id, task_id, idx, channel) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (tid, checkpoint, "task", 0, "count"),
                    )
    return path


def _rows(db):
    with closing(sqlite3.connect(db)) as conn:
        return {table: set(conn.execute(f"SELECT * FROM {table}")) for table in TABLES}


def test_clears_only_original_thread_and_repeats_safely(db):
    """Provisional: REQ-C-LOCAL-CKPT-008 and INV-C-LOCAL-CKPT-008."""
    before = _rows(db)
    assert all({row[0] for row in rows} == {ORIGINAL, NEIGHBOR, LEGACY} for rows in before.values())
    survivors = {table: {row for row in rows if row[0] != ORIGINAL} for table, rows in before.items()}

    assert checkpointer.clear_checkpoint_thread(str(db), ORIGINAL) is True
    assert _rows(db) == survivors
    assert checkpointer.clear_checkpoint_thread(db, ORIGINAL) is False
    assert _rows(db) == survivors


@pytest.mark.parametrize("empty_table", TABLES)
def test_returns_true_when_only_one_table_has_target_rows(db, empty_table):
    """Provisional: REQ-C-LOCAL-CKPT-008."""
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute(f"DELETE FROM {empty_table} WHERE thread_id = ?", (ORIGINAL,))
    before = _rows(db)
    assert checkpointer.clear_checkpoint_thread(db, ORIGINAL) is True
    assert _rows(db) == {
        table: {row for row in rows if row[0] != ORIGINAL} for table, rows in before.items()
    }


def test_second_delete_failure_rolls_back_first_delete(db):
    """Provisional: INV-C-LOCAL-CKPT-008."""
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("""
            CREATE TRIGGER fail_checkpoint_delete BEFORE DELETE ON checkpoints
            WHEN NOT EXISTS (SELECT 1 FROM writes WHERE thread_id = OLD.thread_id)
            BEGIN
                SELECT RAISE(FAIL, 'writes removed before checkpoint delete failed');
            END
        """)
    before = _rows(db)

    with pytest.raises(sqlite3.IntegrityError, match="writes removed before checkpoint delete failed"):
        checkpointer.clear_checkpoint_thread(db, ORIGINAL)

    assert _rows(db) == before


@pytest.mark.parametrize("nested", [False, True], ids=["existing-parent", "missing-parent"])
def test_missing_database_does_not_touch_filesystem(tmp_path, nested):
    """Provisional: INV-C-LOCAL-CKPT-008."""
    db = (tmp_path / "missing" if nested else tmp_path) / "original #1.db"
    assert checkpointer.clear_checkpoint_thread(db, ORIGINAL) is False
    assert list(tmp_path.iterdir()) == []


def test_schema_error_surfaces_without_creating_tables(tmp_path):
    """Provisional: INV-C-LOCAL-CKPT-008."""
    db = tmp_path / "incomplete.db"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE writes (thread_id TEXT)")
        conn.execute("INSERT INTO writes VALUES (?)", (ORIGINAL,))

    with pytest.raises(sqlite3.OperationalError, match="no such table: checkpoints"):
        checkpointer.clear_checkpoint_thread(db, ORIGINAL)

    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT * FROM writes").fetchall() == [(ORIGINAL,)]
        assert conn.execute("SELECT name FROM sqlite_schema WHERE type = 'table'").fetchall() == [
            ("writes",)
        ]
