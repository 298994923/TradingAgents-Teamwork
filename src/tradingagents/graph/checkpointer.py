"""LangGraph checkpoint support for resumable analysis runs.

Per-ticker SQLite databases so concurrent tickers don't contend.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Generator
from contextlib import closing, contextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from tradingagents.dataflows.symbols import safe_ticker_component


def _db_path(data_dir: str | Path, ticker: str) -> Path:
    """Return the SQLite checkpoint DB path for a ticker."""
    # Reject ticker values that would escape the checkpoints directory.
    safe = safe_ticker_component(ticker).upper()
    p = Path(data_dir) / "checkpoints"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{safe}.db"


def thread_id(ticker: str, date: str, signature: str = "", *, run_key: str = "") -> str:
    """Deterministic thread ID for a ticker, date, and optional run key.

    ``signature`` folds in graph-shape-affecting run choices so a resume under a
    different graph can't reuse this checkpoint (#1089). ``run_key`` separates
    individual runs without changing the signature. An empty key preserves the
    original ID.
    """
    if run_key:
        import json

        base = json.dumps(
            ["checkpoint-thread-v1", ticker.upper(), date, signature, run_key],
            ensure_ascii=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(base.encode("ascii")).hexdigest()[:16]

    base = f"{ticker.upper()}:{date}"
    if signature:
        base = f"{base}:{signature}"
    return hashlib.sha256(base.encode()).hexdigest()[:16]


@contextmanager
def get_checkpointer(data_dir: str | Path, ticker: str) -> Generator[SqliteSaver, None, None]:
    """Context manager yielding a SqliteSaver backed by a per-ticker DB."""
    db = _db_path(data_dir, ticker)
    conn = sqlite3.connect(str(db), check_same_thread=False)
    try:
        saver = SqliteSaver(conn)
        saver.setup()
        yield saver
    finally:
        conn.close()


def checkpoint_step(
    data_dir: str | Path, ticker: str, date: str, signature: str = "", *, run_key: str = ""
) -> int | None:
    """Return the latest checkpoint step for the requested thread, or None."""
    db = _db_path(data_dir, ticker)
    if not db.exists():
        return None
    tid = thread_id(ticker, date, signature, run_key=run_key)
    with get_checkpointer(data_dir, ticker) as saver:
        config = {"configurable": {"thread_id": tid}}
        cp = saver.get_tuple(config)
        if cp is None:
            return None
        return cp.metadata.get("step")


def checkpoint_thread_exists(db: str | Path, thread_id: str) -> bool:
    """Check the locator's exact thread without reading or changing its state.

    A missing database or thread returns False; storage errors propagate.
    """
    path = Path(db).absolute()
    try:
        conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    except sqlite3.OperationalError as exc:
        if exc.sqlite_errorcode == sqlite3.SQLITE_CANTOPEN:
            # SQLite uses CANTOPEN for access failures as well as missing files.
            try:
                path.stat()
            except FileNotFoundError:
                return False
        raise

    try:
        return conn.execute(
            "SELECT 1 FROM checkpoints WHERE thread_id = ? LIMIT 1", (thread_id,),
        ).fetchone() is not None
    finally:
        conn.close()


def clear_all_checkpoints(data_dir: str | Path) -> int:
    """Remove all checkpoint databases. Returns the number of databases deleted.

    SQLite keeps committed state in ``-wal`` and ``-shm`` files beside the
    database, so deleting only the ``.db`` leaves a cleared checkpoint with data
    still on disk.
    """
    cp_dir = Path(data_dir) / "checkpoints"
    if not cp_dir.exists():
        return 0
    dbs = list(cp_dir.glob("*.db"))
    for db in dbs:
        for path in (db, *cp_dir.glob(f"{db.name}-*")):
            path.unlink(missing_ok=True)
    return len(dbs)


def clear_checkpoint(
    data_dir: str | Path, ticker: str, date: str, signature: str = "", *, run_key: str = ""
) -> None:
    """Delete the checkpoint and write rows for the requested thread."""
    db = _db_path(data_dir, ticker)
    if not db.exists():
        return
    tid = thread_id(ticker, date, signature, run_key=run_key)
    conn = sqlite3.connect(str(db))
    try:
        for table in ("writes", "checkpoints"):
            conn.execute(f"DELETE FROM {table} WHERE thread_id = ?", (tid,))
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()


def clear_checkpoint_thread(db: str | Path, thread_id: str) -> bool:
    """Delete the exact thread from the caller-validated original database.

    Call only after durably publishing a successful terminal manifest. Return
    False for a missing database or thread; storage errors propagate.
    """
    path = Path(db).absolute()
    try:
        conn = sqlite3.connect(f"{path.as_uri()}?mode=rw", uri=True)
    except sqlite3.OperationalError as exc:
        if exc.sqlite_errorcode == sqlite3.SQLITE_CANTOPEN:
            # Distinguish an absent database from access and other open failures.
            try:
                path.stat()
            except FileNotFoundError:
                return False
        raise

    with closing(conn), conn:
        writes = conn.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,)).rowcount
        checkpoints = conn.execute(
            "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,),
        ).rowcount
    return writes > 0 or checkpoints > 0
