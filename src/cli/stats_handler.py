"""Callback handler tracking LLM/tool calls and per-call token usage (E2).

Per-call usage follows ``docs/handoffs/E-interfaces-v1.md`` §E2: every LLM call is a
``CallUsage`` keyed by its LangChain ``run_id``. The aggregate entry stays
``get_stats()``; ``llm_calls`` counts start-callback events (one invoke emitting two
starts counts as two), not SDK retries.

Settlement rule for a window of calls: if every call is ``reported`` or
``explicit_zero`` the tokens sum once; if any call is ``partial``/``invalid``/
``missing``/``failed`` the window is ``None`` (unknown), never a fabricated number.

``track(stage)`` scopes the call ids seen while it is active using a ``ContextVar``,
so concurrent threads/tasks do not see each other's ids. At context exit the window
is closed atomically and frozen into a ``StageSettlement`` (see ``settle``): the
handle's ``call_ids`` and ``settlement`` never change afterwards. A late callback
can still update the handler's global records, but it cannot extend a closed
window, cannot rewrite a frozen settlement, and cannot turn a settled ``None``
into a refund.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult

# Statuses that make a settled window unknown (any one -> None for the window).
_UNKNOWN_STATUSES = frozenset({"partial", "invalid", "missing", "failed"})


class _StageWindow:
    """Mutable collector for one ``track`` window; closed once at context exit.

    ``closed`` is the important part: a context copied into another thread or an
    asyncio task keeps a reference to this object, so a late callback must be
    refused explicitly instead of relying only on ``ContextVar.reset`` (which
    affects only the context that opened the window).
    """

    def __init__(self, stage: str) -> None:
        self.stage = stage
        self.ids: list[str] = []
        # Call ids whose start callback fired while this window was active. Recorded
        # at start time (before the delayed ``_collect`` membership step), so an
        # in-flight start that has not yet joined ``ids`` is still known to *this*
        # window and cannot be confused with an old unrelated unfinished call.
        self.started: set[str] = set()
        self.closed = False
        self._lock = threading.Lock()

    def record_started(self, call_id: str) -> None:
        with self._lock:
            if not self.closed:
                self.started.add(call_id)

    def record(self, call_id: str) -> None:
        with self._lock:
            if not self.closed and call_id not in self.ids:
                self.ids.append(call_id)

    def close(self) -> tuple[str, ...]:
        with self._lock:
            self.closed = True
            return tuple(self.ids)

    def started_ids(self) -> set[str]:
        with self._lock:
            return set(self.started)


# The collector for the innermost active ``track`` in the current context, if any.
_active_collector: ContextVar[_StageWindow | None] = ContextVar(
    "stats_active_collector", default=None
)


@dataclass(frozen=True)
class CallUsage:
    """One LLM call's usage, keyed by the LangChain ``run_id``."""

    call_id: str
    node: str | None
    status: str  # reported | explicit_zero | partial | invalid | missing | failed
    source: str  # usage_metadata | token_usage | none
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None  # E local input+output; provider ``total`` not trusted


@dataclass(frozen=True)
class StageSettlement:
    """An immutable snapshot of one ``track`` window, frozen at context exit.

    ``units`` is ``sum(total_tokens)`` only when the window is complete:
    every recorded call is ``reported``/``explicit_zero`` with a usable total
    **and** the observed id count matches ``expected_calls`` (when the caller
    declared it). Otherwise ``units`` is ``None``. A later callback never
    changes this object, so an unknown settlement cannot become a refund, and
    a partial window cannot be mistaken for a complete one.
    """

    stage: str
    call_ids: tuple[str, ...]
    usages: tuple[tuple[str, CallUsage | None], ...]
    pending: tuple[str, ...]
    units: int | None
    complete: bool
    expected_calls: int | None
    count_matches: bool


class TrackHandle:
    """The result of ``track(stage)``: ids seen while active, frozen at exit."""

    def __init__(self, stage: str, window: _StageWindow) -> None:
        self.stage = stage
        self._window = window
        self._settlement: StageSettlement | None = None

    def _freeze(self, settlement: StageSettlement) -> None:
        self._settlement = settlement

    @property
    def call_ids(self) -> tuple[str, ...]:
        if self._settlement is not None:
            return self._settlement.call_ids
        return tuple(self._window.ids)

    @property
    def settlement(self) -> StageSettlement:
        if self._settlement is None:
            raise RuntimeError(
                "stage window is still open; the settlement is frozen when track() exits"
            )
        return self._settlement


def _as_int(value: Any) -> int | None:
    """A non-negative int from ``value``, or ``None`` when it is not a valid count."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


class StatsCallbackHandler(BaseCallbackHandler):
    """Track LLM calls, tool calls, and per-call token usage."""

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self.llm_calls = 0
        self.tool_calls = 0
        # Legacy manual counters (kept for callers that set them directly, e.g. tests).
        self.tokens_in = 0
        self.tokens_out = 0
        self._usage_reported = False
        # Per-call records, insertion-ordered by first observation.
        self._calls: dict[str, CallUsage] = {}

    # --- callbacks ----------------------------------------------------------

    def on_llm_start(self, serialized, prompts, **kwargs: Any) -> None:
        self._on_start(kwargs)

    def on_chat_model_start(self, serialized, messages, **kwargs: Any) -> None:
        self._on_start(kwargs)

    def _on_start(self, kwargs: dict[str, Any]) -> None:
        run_id = kwargs.get("run_id")
        if run_id is None:
            return
        call_id = str(run_id)
        metadata = kwargs.get("metadata") or {}
        node = metadata.get("langgraph_node")
        with self._lock:
            self.llm_calls += 1
            # A start without a completed end is "missing" until an end arrives.
            self._calls[call_id] = CallUsage(
                call_id=call_id,
                node=node,
                status="missing",
                source="none",
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
            )
            # Tell the active window this call started here, before the (possibly
            # delayed) ``_collect`` membership step. This is what lets the freeze
            # see an in-flight start without scanning (and being polluted by)
            # unrelated, older unfinished calls.
            window = _active_collector.get()
            if window is not None:
                window.record_started(call_id)
        self._collect(call_id)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        if run_id is None:
            return
        call_id = str(run_id)
        usage = self._extract_usage(response)
        with self._lock:
            node = self._calls[call_id].node if call_id in self._calls else None
            self._calls[call_id] = self._settle(call_id, node, usage)
        self._collect(call_id)

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        if run_id is None:
            return
        call_id = str(run_id)
        with self._lock:
            node = self._calls[call_id].node if call_id in self._calls else None
            self._calls[call_id] = CallUsage(
                call_id=call_id,
                node=node,
                status="failed",
                source="none",
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
            )
        self._collect(call_id)

    def on_tool_start(self, serialized, input_str, **kwargs: Any) -> None:
        with self._lock:
            self.tool_calls += 1

    # --- usage extraction / settlement -------------------------------------

    @staticmethod
    def _extract_usage(response: LLMResult) -> tuple[str, Any]:
        """Return ``(source, usage_dict)`` from a response; ``("none", None)`` if absent."""
        try:
            generation = response.generations[0][0]
        except (IndexError, TypeError):
            return "none", None
        message = getattr(generation, "message", None)
        if not isinstance(message, AIMessage):
            return "none", None
        usage_metadata = getattr(message, "usage_metadata", None)
        if usage_metadata:
            return "usage_metadata", usage_metadata
        token_usage = getattr(message, "response_metadata", {}).get("token_usage")
        if token_usage:
            return "token_usage", token_usage
        return "none", None

    @staticmethod
    def _settle(call_id: str, node: str | None, usage: tuple[str, Any]) -> CallUsage:
        source, data = usage
        if data is None:
            return CallUsage(call_id, node, "missing", "none", None, None, None)
        input_tokens = _as_int(data.get("input_tokens", data.get("prompt_tokens")))
        output_tokens = _as_int(data.get("output_tokens", data.get("completion_tokens")))
        if input_tokens is None and output_tokens is None:
            status = "invalid"
        elif input_tokens is None or output_tokens is None:
            status = "partial"
        elif input_tokens == 0 and output_tokens == 0:
            status = "explicit_zero"
        else:
            status = "reported"
        total = (
            input_tokens + output_tokens
            if input_tokens is not None and output_tokens is not None
            else None
        )
        return CallUsage(
            call_id, node, status, source, input_tokens, output_tokens, total
        )

    # --- query --------------------------------------------------------------

    def calls(self) -> tuple[CallUsage, ...]:
        with self._lock:
            return tuple(self._calls.values())

    def call(self, call_id: str) -> CallUsage | None:
        with self._lock:
            return self._calls.get(call_id)

    @contextmanager
    def track(self, stage: str, *, expected_calls: int | None = None):
        """Collect ids while active, then atomically close and freeze a settlement.

        ``expected_calls`` is the number of callback ids the caller admitted for
        this stage. Declaring it makes a window with fewer ids than expected
        ``units=None`` instead of a partial sum -- this is the answer to C's
        "one complete callback, another not collected at the exit boundary"
        case. Without a declared count, a window that simply saw fewer callbacks
        cannot be distinguished from a complete one, so callers that need that
        guarantee must declare it.

        The freeze takes ``self._lock``, so it cannot race a callback writing a
        new ``CallUsage``. ``window.close()`` marks the window closed first; a
        copied context that still holds the window is refused from then on.
        Callbacks must finish inside the ``with`` block: anything arriving after
        the freeze only updates the handler's global records.
        """
        if expected_calls is not None and (
            isinstance(expected_calls, bool)
            or not isinstance(expected_calls, int)
            or expected_calls < 0
        ):
            raise ValueError("expected_calls must be a non-negative int or None")
        window = _StageWindow(stage)
        handle = TrackHandle(stage, window)
        token = _active_collector.set(window)
        try:
            yield handle
        finally:
            with self._lock:
                ids = window.close()
                usages = tuple((cid, self._calls.get(cid)) for cid in ids)
                collected = set(ids)
                # Race guard, scoped to this window: a start callback writes its
                # global record (and registers in ``window.started``) under this
                # lock, before the possibly-delayed ``_collect`` membership step.
                # Any call that started in this window but is not yet in ``ids`` and
                # is still unfinalized is in flight: report the window unknown
                # rather than a complete partial sum. Calls from earlier windows are
                # not in this window's ``started`` set and so cannot poison it.
                inflight = tuple(
                    cid
                    for cid in sorted(window.started_ids() - collected)
                    if (self._calls.get(cid) is None
                        or self._calls[cid].status in _UNKNOWN_STATUSES)
                )
                pending = tuple(
                    cid for cid, usage in usages
                    if usage is None or usage.status in _UNKNOWN_STATUSES
                ) + inflight
                count_matches = expected_calls is None or len(ids) == expected_calls
                complete = (
                    count_matches
                    and not inflight
                    and bool(ids)
                    and all(
                        usage is not None
                        and usage.status in {"reported", "explicit_zero"}
                        and usage.total_tokens is not None
                        for _, usage in usages
                    )
                )
                units = (
                    sum(usage.total_tokens or 0 for _, usage in usages if usage is not None)
                    if complete else None
                )
                handle._freeze(StageSettlement(
                    stage=stage,
                    call_ids=ids,
                    usages=usages,
                    pending=pending,
                    units=units,
                    complete=complete,
                    expected_calls=expected_calls,
                    count_matches=count_matches,
                ))
            _active_collector.reset(token)

    def settle(self, handle: TrackHandle) -> StageSettlement:
        """Return the immutable settlement for a closed ``track`` window.

        This is the public entry C should call once, immediately after the
        ``with stats.track(stage)`` block, then pass ``units`` to
        ``BudgetPolicy.record_usage(stage, units)`` (``None`` when unknown).
        """
        return handle.settlement

    def _collect(self, call_id: str) -> None:
        window = _active_collector.get()
        if window is not None:
            window.record(call_id)

    # --- aggregate ----------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Aggregate stats; token counts are null when unknown.

        When at least one call has been observed, tokens settle over the recorded
        calls: none are invented for a window containing a partial/invalid/missing/
        failed call. With no recorded calls, the legacy manual counters apply (still
        ``None`` until usage was reported).
        """
        with self._lock:
            if self._calls:
                return self._settle_window()
            return {
                "llm_calls": self.llm_calls,
                "tool_calls": self.tool_calls,
                "tokens_in": self.tokens_in if self._usage_reported else None,
                "tokens_out": self.tokens_out if self._usage_reported else None,
            }

    def _settle_window(self) -> dict[str, Any]:
        calls = list(self._calls.values())
        if any(call.status in _UNKNOWN_STATUSES for call in calls):
            tokens_in = tokens_out = None
        else:
            tokens_in = sum(call.input_tokens for call in calls)
            tokens_out = sum(call.output_tokens for call in calls)
        return {
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
