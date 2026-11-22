"""Callback handler tracking LLM/tool calls and per-call token usage (E2).

Per-call usage follows ``docs/handoffs/E-interfaces-v1.md`` §E2: every LLM call is a
``CallUsage`` keyed by its LangChain ``run_id``. The aggregate entry stays
``get_stats()``; ``llm_calls`` counts start-callback events (one invoke emitting two
starts counts as two), not SDK retries.

Settlement rule for a window of calls: if every call is ``reported`` or
``explicit_zero`` the tokens sum once; if any call is ``partial``/``invalid``/
``missing``/``failed`` the window is ``None`` (unknown), never a fabricated number.

``track(stage)`` scopes the call ids seen while it is active using a ``ContextVar``,
so concurrent threads/tasks do not see each other's ids. A late callback only updates
the global record; it never writes back into a handle that has already closed.
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

# The collector for the innermost active ``track`` in the current context, if any.
_active_collector: ContextVar[list[str] | None] = ContextVar(
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


class TrackHandle:
    """The result of ``track(stage)``: the call ids seen while the stage was active."""

    def __init__(self, stage: str) -> None:
        self.stage = stage
        self._ids: list[str] = []

    def _record(self, call_id: str) -> None:
        if call_id not in self._ids:
            self._ids.append(call_id)

    @property
    def call_ids(self) -> tuple[str, ...]:
        return tuple(self._ids)


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
    def track(self, stage: str):
        """Collect the call ids seen while this stage is active (context-isolated)."""
        handle = TrackHandle(stage)
        token = _active_collector.set(handle._ids)
        try:
            yield handle
        finally:
            _active_collector.reset(token)

    def _collect(self, call_id: str) -> None:
        collector = _active_collector.get()
        if collector is not None and call_id not in collector:
            collector.append(call_id)

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
