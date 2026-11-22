"""Offline tests for E2 per-call usage (docs/handoffs/E-interfaces-v1.md §E2).

Covers the frozen interface: ``CallUsage``, ``calls()``, ``call(id)``, ``track(stage)``
with ContextVar isolation. Required cases: concurrency, late callbacks,
missing / failed / explicit-zero, and one invoke producing two starts counted as two
callbacks (llm_calls == 2). Also pins the settlement rule: a window whose calls are
all ``reported``/``explicit_zero`` sums once; any ``partial/invalid/missing/failed``
makes the window ``None``.
"""

from __future__ import annotations

import threading
import uuid

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from cli.stats_handler import CallUsage, StatsCallbackHandler


def _result(input_tokens=None, output_tokens=None) -> LLMResult:
    meta = None
    if input_tokens is not None or output_tokens is not None:
        total = (input_tokens or 0) + (output_tokens or 0)
        meta = {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total}
    msg = AIMessage(content="ok", usage_metadata=meta)
    return LLMResult(generations=[[ChatGeneration(message=msg)]])


def _result_token_usage(**token_usage) -> LLMResult:
    msg = AIMessage(content="ok", response_metadata={"token_usage": token_usage})
    return LLMResult(generations=[[ChatGeneration(message=msg)]])


def _rid() -> uuid.UUID:
    return uuid.uuid4()


def _start(handler, rid, node=None):
    meta = {"langgraph_node": node} if node else None
    handler.on_chat_model_start({}, [[]], run_id=rid, metadata=meta)


def _end(handler, rid, input_tokens=None, output_tokens=None):
    handler.on_llm_end(_result(input_tokens, output_tokens), run_id=rid)


# --- shape of CallUsage ------------------------------------------------------


def test_calls_returns_callusage_tuple():
    h = StatsCallbackHandler()
    rid = _rid()
    _start(h, rid, node="market_analyst")
    _end(h, rid, 10, 5)
    calls = h.calls()
    assert isinstance(calls, tuple)
    cu = calls[0]
    assert isinstance(cu, CallUsage)
    assert cu.call_id == str(rid)
    assert cu.node == "market_analyst"
    assert cu.status == "reported"
    assert cu.source == "usage_metadata"
    assert cu.input_tokens == 10
    assert cu.output_tokens == 5
    assert cu.total_tokens == 15  # E local input+output, not provider total


def test_call_lookup_by_id():
    h = StatsCallbackHandler()
    rid = _rid()
    _start(h, rid)
    _end(h, rid, 1, 1)
    assert h.call(str(rid)).status == "reported"
    assert h.call("does-not-exist") is None


# --- explicit zero / missing / partial / invalid / failed --------------------


def test_explicit_zero_is_reported_not_missing():
    h = StatsCallbackHandler()
    rid = _rid()
    _start(h, rid)
    _end(h, rid, 0, 0)
    cu = h.call(str(rid))
    assert cu.status == "explicit_zero"
    assert cu.input_tokens == 0 and cu.output_tokens == 0
    assert cu.total_tokens == 0


def test_missing_when_no_usage_metadata():
    h = StatsCallbackHandler()
    rid = _rid()
    _start(h, rid)
    _end(h, rid)  # no usage_metadata
    cu = h.call(str(rid))
    assert cu.status == "missing"
    assert cu.source == "none"
    assert cu.input_tokens is None and cu.output_tokens is None


def test_partial_when_one_token_missing():
    h = StatsCallbackHandler()
    rid = _rid()
    _start(h, rid)
    # A provider reporting only prompt tokens: partial, source token_usage.
    h.on_llm_end(_result_token_usage(prompt_tokens=10), run_id=rid)
    cu = h.call(str(rid))
    assert cu.status == "partial"
    assert cu.source == "token_usage"


def test_failed_on_error():
    h = StatsCallbackHandler()
    rid = _rid()
    _start(h, rid)
    h.on_llm_error(RuntimeError("boom"), run_id=rid)
    cu = h.call(str(rid))
    assert cu.status == "failed"
    assert cu.input_tokens is None and cu.output_tokens is None


# --- one invoke, two starts -> two callbacks --------------------------------


def test_two_starts_are_two_calls_and_two_llm_calls():
    h = StatsCallbackHandler()
    rid_a, rid_b = _rid(), _rid()
    # One invoke emitting two start callbacks (e.g. retry inside the SDK wrapper).
    _start(h, rid_a)
    _start(h, rid_b)
    assert len(h.calls()) == 2
    assert h.get_stats()["llm_calls"] == 2  # callback events, not retries collapsed


# --- late callbacks ---------------------------------------------------------


def test_late_end_after_freeze_does_not_rewrite_handle():
    h = StatsCallbackHandler()
    rid = _rid()
    with h.track("market") as handle:
        _start(h, rid)
    frozen = handle.call_ids
    # A late end arrives after the stage window closed.
    _end(h, rid, 99, 1)
    assert handle.call_ids == frozen  # not rewritten
    assert h.call(str(rid)).status == "reported"  # global record did update


def test_end_without_start_is_recorded_globally():
    h = StatsCallbackHandler()
    rid = _rid()
    _end(h, rid, 4, 2)  # no start seen
    cu = h.call(str(rid))
    assert cu is not None
    assert cu.status == "reported"


# --- track(stage) + ContextVar isolation ------------------------------------


def test_track_collects_call_ids_in_context():
    h = StatsCallbackHandler()
    rid = _rid()
    with h.track("news") as handle:
        _start(h, rid)
        _end(h, rid, 1, 1)
    assert str(rid) in handle.call_ids


def test_track_is_isolated_across_threads():
    h = StatsCallbackHandler()
    results = {}

    def worker(name):
        rid = _rid()
        with h.track(name) as handle:
            _start(h, rid)
            _end(h, rid, 1, 1)
        results[name] = (str(rid), handle.call_ids)

    threads = [threading.Thread(target=worker, args=(f"t{i}",)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for name, (rid, ids) in results.items():
        assert ids == (rid,), f"{name} leaked another thread's call id"


def test_nested_tracks_isolated():
    h = StatsCallbackHandler()
    outer_rid, inner_rid = _rid(), _rid()
    with h.track("outer") as outer:
        _start(h, outer_rid)
        with h.track("inner") as inner:
            _start(h, inner_rid)
        assert outer.call_ids == (str(outer_rid),)
        assert inner.call_ids == (str(inner_rid),)


# --- settlement via get_stats() ---------------------------------------------


def test_get_stats_sums_all_reported_window():
    h = StatsCallbackHandler()
    for inp, out in ((10, 5), (20, 10)):
        rid = _rid()
        _start(h, rid)
        _end(h, rid, inp, out)
    stats = h.get_stats()
    assert stats["tokens_in"] == 30
    assert stats["tokens_out"] == 15


def test_get_stats_sums_explicit_zero_with_reported():
    h = StatsCallbackHandler()
    for inp, out in ((0, 0), (10, 5)):
        rid = _rid()
        _start(h, rid)
        _end(h, rid, inp, out)
    assert h.get_stats()["tokens_in"] == 10


def test_get_stats_none_when_any_missing():
    h = StatsCallbackHandler()
    a, b = _rid(), _rid()
    _start(h, a)
    _end(h, a, 10, 5)
    _start(h, b)
    _end(h, b)  # missing
    assert h.get_stats()["tokens_in"] is None
    assert h.get_stats()["tokens_out"] is None


def test_get_stats_none_when_any_failed():
    h = StatsCallbackHandler()
    a = _rid()
    _start(h, a)
    h.on_llm_error(RuntimeError("x"), run_id=a)
    assert h.get_stats()["tokens_in"] is None


def test_total_tokens_is_local_sum():
    h = StatsCallbackHandler()
    rid = _rid()
    _start(h, rid)
    _end(h, rid, 7, 3)
    assert h.call(str(rid)).total_tokens == 10
