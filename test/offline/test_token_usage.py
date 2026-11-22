"""Offline tests for token-usage reporting: missing tokens are null, shown as --.

The runtime path (not just compare_runs) must not report 0 for an unreported token
count. ``StatsCallbackHandler.get_stats`` returns ``None`` for tokens when no call
ever reported usage, and the live display renders ``--`` for them without crashing.
"""

from cli.display import _format_token_line
from cli.stats_handler import StatsCallbackHandler

# --- stats handler: missing tokens are null ----------------------------------


def test_no_usage_reported_tokens_are_none():
    stats = StatsCallbackHandler().get_stats()
    assert stats["tokens_in"] is None
    assert stats["tokens_out"] is None
    # Call counters are genuinely measured, so 0 is correct there.
    assert stats["llm_calls"] == 0
    assert stats["tool_calls"] == 0


def test_reported_usage_yields_numbers():
    handler = StatsCallbackHandler()
    handler.tokens_in = 0  # simulate a call that reported zero
    handler._usage_reported = True
    stats = handler.get_stats()
    assert stats["tokens_in"] == 0
    assert stats["tokens_out"] == 0


def test_partial_usage_accumulates():
    handler = StatsCallbackHandler()
    handler._usage_reported = True
    handler.tokens_in = 1234
    handler.tokens_out = 56
    stats = handler.get_stats()
    assert stats["tokens_in"] == 1234
    assert stats["tokens_out"] == 56


# --- display: -- for null, no crash ------------------------------------------


def test_token_line_dash_when_none():
    line = _format_token_line({"tokens_in": None, "tokens_out": None})
    assert line == "Tokens: --"


def test_token_line_dash_when_zero_and_unreported_semantics():
    # Explicit zeros still format as a real (zero) count; only None is unknown.
    line = _format_token_line({"tokens_in": 0, "tokens_out": 0})
    assert line == "Tokens: 0\u2191 0\u2193"


def test_token_line_formats_numbers():
    line = _format_token_line({"tokens_in": 2000, "tokens_out": 500})
    assert line == "Tokens: 2.0k\u2191 500\u2193"


def test_token_line_single_none_side_is_dash():
    # If one side is unknown, do not fabricate a number for it.
    line = _format_token_line({"tokens_in": None, "tokens_out": 500})
    assert line == "Tokens: --"
