"""Guard-to-report masking: a non-executable verdict drops the trade proposals.

When ``final_state["guard_result"]`` has ``executable is False`` (BLOCK / REVIEW),
the public report must not contain the trader plan or the portfolio proposal; the
decision is replaced by the guard verdict and reason. Analyst evidence stays. Runs
with no ``guard_result`` are unchanged, and PASS (executable True) keeps proposals.

Covers both ``reporting.write_report_tree`` (markdown tree + section files) and
``report_html.render_report`` so the HTML page cannot leak either.
"""

from __future__ import annotations

import re
from html import unescape

from tradingagents.reporting import write_report_tree

TICKER = "AAPL"
ANALYST_EVIDENCE = "ANALYST-EVIDENCE: volume was above its monthly median."
TRADER_TEXT = (
    "**Rating**: Buy [TRADER-RATING]\n\n"
    "**Entry Price**: 123.456789\n\n"
    "**Action**: Buy [TRADER-ACTION]\n\n"
    "FINAL TRANSACTION PROPOSAL: Buy [TRADER-PROPOSAL]"
)
PM_TEXT = (
    "Rating: Overweight 678.987654 [PM-PRICE]\n\n"
    "Action: Buy [PM-ACTION]\n\n"
    "FINAL TRANSACTION PROPOSAL: Buy [PM-PROPOSAL]"
)
PROPOSAL_LINE = "FINAL TRANSACTION PROPOSAL:"

TRADER_MARKERS = ["TRADER-RATING", "123.456789", "TRADER-ACTION", "TRADER-PROPOSAL"]
PM_MARKERS = ["Rating: Overweight", "678.987654", "PM-ACTION", "PM-PROPOSAL"]


def _state(guard_result=None):
    state = {
        "company_of_interest": TICKER,
        "trade_date": "2026-01-09",
        "market_report": ANALYST_EVIDENCE,
        "investment_plan": "Research notes on the volume pattern.",
        "trader_investment_plan": TRADER_TEXT,
        "final_trade_decision": PM_TEXT,
    }
    if guard_result is not None:
        state["guard_result"] = guard_result
    return state


def _guard(verdict, executable, reason_code):
    return {
        "contract": "validation-decision/1.1",
        "verdict": verdict,
        "reason_code": reason_code,
        "checkpoint": "final",
        "executable": executable,
        "rules_hit": [],
    }


def _text(path):
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".html":
        raw = unescape(re.sub(r"<[^>]+>", "", raw))
    return " ".join(raw.replace("**", "").split())


def _artifacts(root):
    return {p.relative_to(root).as_posix(): _text(p) for p in root.rglob("*") if p.is_file()}


def _assert_no_leak(artifacts):
    forbidden = TRADER_MARKERS + PM_MARKERS + [f"{PROPOSAL_LINE} Buy [TRADER-PROPOSAL]",
                                              f"{PROPOSAL_LINE} Buy [PM-PROPOSAL]"]
    leaks = [
        f"{name}: {marker!r}"
        for name, text in sorted(artifacts.items())
        for marker in forbidden if marker in text
    ]
    assert not leaks, "\n".join(leaks)
    assert all(PROPOSAL_LINE not in text for text in artifacts.values())


# --- non-executable: BLOCK / REVIEW -----------------------------------------


def test_block_drops_trader_and_replaces_decision(tmp_path):
    final_state = _state(_guard("BLOCK", False, "CAP_EXCEEDED"))
    write_report_tree(final_state, TICKER, tmp_path, html=True)
    artifacts = _artifacts(tmp_path)

    # Analyst evidence and research kept; trader section gone.
    assert ANALYST_EVIDENCE in artifacts["complete_report.md"]
    assert ANALYST_EVIDENCE in artifacts["1_analysts/market.md"]
    assert "3_trading/trader.md" not in artifacts
    # Decision file exists but carries the guard disposition, not the proposal.
    disposition = "GUARD BLOCK (CAP_EXCEEDED): non-executable disposition"
    assert disposition in artifacts["5_portfolio/decision.md"]
    assert disposition in artifacts["complete_report.md"]
    assert disposition in artifacts["complete_report.html"]

    _assert_no_leak(artifacts)


def test_review_drops_trader_and_replaces_decision(tmp_path):
    final_state = _state(_guard("REVIEW", False, "POSITION_UNKNOWN"))
    write_report_tree(final_state, TICKER, tmp_path, html=False)
    artifacts = _artifacts(tmp_path)
    assert ANALYST_EVIDENCE in artifacts["complete_report.md"]
    assert "3_trading/trader.md" not in artifacts
    disposition = "GUARD REVIEW (POSITION_UNKNOWN): non-executable disposition"
    assert disposition in artifacts["5_portfolio/decision.md"]
    # No HTML written when html=False.
    assert "complete_report.html" not in artifacts
    _assert_no_leak(artifacts)


# --- executable: PASS keeps proposals ---------------------------------------


def test_pass_keeps_trader_and_portfolio_proposals(tmp_path):
    final_state = _state(_guard("PASS", True, "PASS"))
    write_report_tree(final_state, TICKER, tmp_path, html=True)
    artifacts = _artifacts(tmp_path)
    assert "3_trading/trader.md" in artifacts
    for marker in TRADER_MARKERS:
        assert marker in artifacts["complete_report.md"], marker
        assert marker in artifacts["3_trading/trader.md"], marker
    for marker in PM_MARKERS:
        assert marker in artifacts["complete_report.md"], marker
    assert PROPOSAL_LINE in artifacts["complete_report.md"]


# --- no guard_result: unchanged behaviour -----------------------------------


def test_no_guard_result_is_unchanged(tmp_path):
    final_state = _state(guard_result=None)
    write_report_tree(final_state, TICKER, tmp_path, html=False)
    artifacts = _artifacts(tmp_path)
    assert "3_trading/trader.md" in artifacts
    assert artifacts["3_trading/trader.md"] == " ".join(TRADER_TEXT.replace("**", "").split())
    for marker in TRADER_MARKERS:
        assert marker in artifacts["complete_report.md"], marker
    for marker in PM_MARKERS:
        assert marker in artifacts["complete_report.md"], marker


def test_guard_result_executable_true_but_unknown_verdict_behaves_as_executable(tmp_path):
    # Only executable is False masks; executable True (any verdict label) keeps proposals.
    final_state = _state({"executable": True})
    write_report_tree(final_state, TICKER, tmp_path, html=False)
    artifacts = _artifacts(tmp_path)
    assert "3_trading/trader.md" in artifacts


# --- rewrite: PASS then BLOCK in the same directory -------------------------


def test_pass_then_block_removes_trader_section_file(tmp_path):
    write_report_tree(_state(_guard("PASS", True, "PASS")), TICKER, tmp_path, html=True)
    assert (tmp_path / "3_trading" / "trader.md").exists()

    write_report_tree(_state(_guard("BLOCK", False, "CAP_EXCEEDED")), TICKER, tmp_path, html=True)
    artifacts = _artifacts(tmp_path)
    # The stale executable proposal section file is reconciled away.
    assert "3_trading/trader.md" not in artifacts
    assert (tmp_path / "3_trading" / "trader.md").exists() is False
    _assert_no_leak(artifacts)


# --- HTML renderer directly -------------------------------------------------


def test_render_report_blocked_suppresses_rating(tmp_path):
    final_state = _state(_guard("BLOCK", False, "CAP_EXCEEDED"))
    write_report_tree(final_state, TICKER, tmp_path, html=True)
    page = _text(tmp_path / "complete_report.html")
    # The tradeable rating the PM wrote must not appear in the masthead.
    assert "Overweight" not in page
    assert "GUARD BLOCK (CAP_EXCEEDED)" in page
    _assert_no_leak(_artifacts(tmp_path))
