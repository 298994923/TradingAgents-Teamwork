"""Frozen stage-window settlement (E's answer to C's usage-window probes).

The public entry is ``StatsCallbackHandler.settle(handle)`` (or
``handle.settlement``) after ``with stats.track(stage)`` exits. It returns an
immutable ``StageSettlement`` with the exact ids, per-id usage, pending ids and
one settlement value. Late callbacks may still update the handler's global
records, but never a closed window or a frozen settlement.
"""

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from dataclasses import FrozenInstanceError
from threading import Barrier
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from cli.stats_handler import StageSettlement, StatsCallbackHandler
from tradingagents.execution_policy import FOLLOW_UP, BudgetPolicy


def _start(handler):
    rid = uuid4()
    handler.on_chat_model_start({}, [[]], run_id=rid)
    return rid


def _end(handler, rid, tokens=(1, 1)):
    usage = None
    if tokens is not None:
        inp, out = tokens
        usage = {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}
    msg = AIMessage(content="scripted", usage_metadata=usage)
    handler.on_llm_end(LLMResult(generations=[[ChatGeneration(message=msg)]]), run_id=rid)


def _error(handler, rid):
    handler.on_llm_error(RuntimeError("boom"), run_id=rid)


def _admitted():
    budget = BudgetPolicy(20)
    assert budget.reserve_final_review(5).allowed
    assert budget.admit(FOLLOW_UP, 10).allowed
    assert budget.available_units == 10
    return budget


# --- 1. complete windows: one sum, once --------------------------------------


@pytest.mark.parametrize(
    ("callbacks", "statuses", "units", "balance"),
    [([(2, 1), (1, 2)], ("reported", "reported"), 6, 14),
     ([(0, 0)], ("explicit_zero",), 0, 20)],
    ids=["multi-callback", "explicit-zero"],
)
def test_complete_window_settles_one_admission(callbacks, statuses, units, balance):
    handler, budget = StatsCallbackHandler(), _admitted()
    with handler.track(FOLLOW_UP) as handle:
        rids = [_start(handler) for _ in callbacks]
        for rid, tokens in zip(rids, callbacks, strict=True):
            _end(handler, rid, tokens)

    settlement = handler.settle(handle)
    assert isinstance(settlement, StageSettlement)
    assert settlement.stage == FOLLOW_UP
    assert settlement.call_ids == tuple(map(str, rids))
    assert tuple(row.status for _, row in settlement.usages) == statuses
    assert settlement.pending == ()
    assert settlement.complete is True
    assert settlement.units == units

    budget.record_usage(FOLLOW_UP, settlement.units)
    usage = budget.usage_for(FOLLOW_UP)
    assert (usage.status, usage.reported_units) == ("reported", units)
    assert budget.available_units == balance
    assert budget.final_review_reserved_units == 5
    with pytest.raises(ValueError, match="no pending admission"):
        budget.record_usage(FOLLOW_UP, units)  # one admission, one settlement


def test_empty_window_is_unknown_not_zero():
    handler = StatsCallbackHandler()
    with handler.track(FOLLOW_UP) as handle:
        pass
    settlement = handler.settle(handle)
    assert settlement.call_ids == ()
    assert settlement.units is None
    assert settlement.complete is False


# --- 2. pending / late callbacks: no refund ---------------------------------


def test_pending_at_exit_then_late_end_does_not_refund():
    handler, budget = StatsCallbackHandler(), _admitted()
    with handler.track(FOLLOW_UP) as handle:
        complete, late = _start(handler), _start(handler)
        _end(handler, complete, (1, 1))

    settlement = handler.settle(handle)
    assert settlement.call_ids == (str(complete), str(late))
    assert tuple(row.status for _, row in settlement.usages) == ("reported", "missing")
    assert settlement.pending == (str(late),)
    assert settlement.units is None
    assert settlement.complete is False
    budget.record_usage(FOLLOW_UP, settlement.units)
    assert budget.usage_for(FOLLOW_UP).status == "unknown"
    assert budget.available_units == 10

    frozen_call_ids = settlement.call_ids
    frozen_units = settlement.units
    _end(handler, late, (1, 1))

    # Global records may update; the frozen window and its settlement cannot.
    assert handler.call(str(late)).status == "reported"
    assert handler.get_stats()["tokens_in"] == 2
    assert handle.call_ids == frozen_call_ids
    assert settlement.call_ids == frozen_call_ids
    assert settlement.units is frozen_units is None
    assert settlement.pending == (str(late),)
    # No second settlement, no refund.
    with pytest.raises(ValueError, match="no pending admission"):
        budget.record_usage(FOLLOW_UP, 2)
    assert budget.usage_for(FOLLOW_UP).status == "unknown"
    assert budget.available_units == 10


def test_pending_and_terminal_missing_are_both_unknown():
    handler = StatsCallbackHandler()
    with handler.track(FOLLOW_UP) as handle:
        pending, terminal = _start(handler), _start(handler)
        _end(handler, terminal, None)
    settlement = handler.settle(handle)
    assert settlement.units is None
    assert set(settlement.pending) == {str(pending), str(terminal)}
    for _, row in settlement.usages:
        assert (row.status, row.source) == ("missing", "none")
        assert row.total_tokens is None


def test_partial_and_failed_make_window_unknown():
    handler = StatsCallbackHandler()
    with handler.track(FOLLOW_UP) as handle:
        partial = _start(handler)
        # A provider that reports only one side arrives via response_metadata;
        # usage_metadata is a pydantic model requiring all three counters.
        msg = AIMessage(content="scripted",
                        response_metadata={"token_usage": {"input_tokens": 3}})
        handler.on_llm_end(
            LLMResult(generations=[[ChatGeneration(message=msg)]]), run_id=partial,
        )
        failed = _start(handler)
        _error(handler, failed)
    settlement = handler.settle(handle)
    assert tuple(row.status for _, row in settlement.usages) == ("partial", "failed")
    assert settlement.units is None
    assert set(settlement.pending) == {str(partial), str(failed)}


def test_settlement_is_immutable():
    handler = StatsCallbackHandler()
    with handler.track(FOLLOW_UP) as handle:
        rid = _start(handler)
        _end(handler, rid, (1, 1))
    settlement = handler.settle(handle)
    with pytest.raises(FrozenInstanceError):
        settlement.units = 999


def test_settle_before_exit_is_refused():
    handler = StatsCallbackHandler()
    with handler.track(FOLLOW_UP) as handle, \
            pytest.raises(RuntimeError, match="still open"):
        handler.settle(handle)


# --- 3. concurrency / inherited context -------------------------------------


def test_concurrent_windows_do_not_mix_callbacks():
    handler = StatsCallbackHandler()
    entered, completed = Barrier(2, timeout=5), Barrier(2, timeout=5)

    def worker(tokens):
        budget = _admitted()
        with handler.track(FOLLOW_UP) as handle:
            rid = _start(handler)
            entered.wait()
            _end(handler, rid, tokens)
            completed.wait()
        settlement = handler.settle(handle)
        budget.record_usage(FOLLOW_UP, settlement.units)
        return str(rid), settlement, budget.usage_for(FOLLOW_UP)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [job.result(timeout=10)
                   for job in [pool.submit(worker, pair) for pair in ((2, 3), (0, 0))]]
    for (rid, settlement, usage), expected in zip(results, (5, 0), strict=True):
        assert settlement.call_ids == (rid,)
        assert len(settlement.usages) == 1
        assert (usage.status, usage.reported_units) == ("reported", expected)
    assert {row.call_id for row in handler.calls()} == {result[0] for result in results}


def test_copied_context_late_start_does_not_extend_closed_handle():
    handler = StatsCallbackHandler()
    with handler.track(FOLLOW_UP) as handle:
        first = _start(handler)
        _end(handler, first, (1, 1))
        inherited = copy_context()
    at_exit = handle.call_ids
    settlement = handler.settle(handle)

    with ThreadPoolExecutor(max_workers=1) as pool:
        late = pool.submit(inherited.run, _start, handler).result(timeout=5)
    _end(handler, late, (1, 1))

    assert at_exit == (str(first),)
    assert handle.call_ids == (str(first),)          # was extendable before the fix
    assert settlement.call_ids == (str(first),)
    assert settlement.units == 2
    assert str(late) not in settlement.call_ids
    # The late call is still visible globally, but not in the closed window.
    assert handler.call(str(late)).status == "reported"
    assert str(late) in {row.call_id for row in handler.calls()}
