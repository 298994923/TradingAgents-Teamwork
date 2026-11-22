"""Pin checkpoint thread IDs without opening any checkpoint storage."""

import pytest

from tradingagents.graph.checkpointer import thread_id

pytestmark = pytest.mark.unit

TICKER = "NVDA"
DATE = "2026-01-09"
SIGNATURE = "sig-a"


def test_legacy_thread_ids_with_omitted_run_key():
    """Provisional: INV-C-LOCAL-CKPT-001."""
    assert thread_id(TICKER, DATE) == "5afe091c9df91d87"
    assert thread_id(TICKER, DATE, SIGNATURE) == "8c7df758d29df99a"
    assert thread_id("nvda", DATE, SIGNATURE) == "8c7df758d29df99a"


def test_legacy_thread_ids_with_empty_run_key():
    """Provisional: INV-C-LOCAL-CKPT-001."""
    assert thread_id(TICKER, DATE, run_key="") == "5afe091c9df91d87"
    assert thread_id(TICKER, DATE, SIGNATURE, run_key="") == "8c7df758d29df99a"


def test_run_scoped_thread_id_is_repeatable_and_normalizes_ticker_case():
    """Provisional: REQ-C-LOCAL-CKPT-001."""
    first = thread_id(TICKER, DATE, SIGNATURE, run_key="r1")
    assert first == thread_id(TICKER, DATE, SIGNATURE, run_key="r1")
    assert first == thread_id("nvda", DATE, SIGNATURE, run_key="r1")


def test_distinct_run_keys_have_distinct_thread_ids():
    """Provisional: REQ-C-LOCAL-CKPT-001."""
    first = thread_id(TICKER, DATE, SIGNATURE, run_key="r1")
    second = thread_id(TICKER, DATE, SIGNATURE, run_key="r2")
    assert first == "7ef0c628b7b5887a"
    assert second == "3194d6e6c58f7f75"
    assert len({first, second, thread_id(TICKER, DATE, SIGNATURE)}) == 3


def test_run_key_cannot_alias_a_legacy_signature_suffix():
    """Provisional: REQ-C-LOCAL-CKPT-001."""
    legacy = thread_id(TICKER, DATE, "sig-a:run=r1")
    scoped = thread_id(TICKER, DATE, SIGNATURE, run_key="r1")
    assert legacy != scoped


def test_run_key_requires_keyword():
    """Provisional: REQ-C-LOCAL-CKPT-001."""
    with pytest.raises(TypeError):
        thread_id(TICKER, DATE, SIGNATURE, "r1")
