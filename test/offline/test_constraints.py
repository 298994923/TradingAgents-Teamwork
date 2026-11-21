"""Verdict API unit tests for D's deterministic guard.

The suite is data-driven from ``test/fixtures/safety_cases.json``. Every test
docstring cites the invariant(s) and requirement(s) it verifies. The current
module is a NAIVE STUB, so positive cases pass and negative/boundary cases are
expected to fail until the real checks land.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from tradingagents.constraints import ABSENT, GuardResult, Verdict, validate

CASES_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "safety_cases.json"
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


def _cases_for(invariant_id: str) -> list[dict]:
    return [case for case in CASES if case["invariant_id"] == invariant_id]


def _kwargs(case: dict) -> dict:
    payload = case["input"]
    return {
        "proposal": payload.get("proposal", {}),
        "portfolio": payload.get("portfolio", ABSENT),
        "stage": case.get("stage", "pm"),
        "prior_verdict": payload.get("prior_verdict"),
        "llm_text": payload.get("llm_text"),
        "config": payload.get("config"),
    }


def _assert_case(case: dict) -> None:
    result = validate(**_kwargs(case))
    assert isinstance(result, GuardResult), f"{case['id']}: expected GuardResult"
    assert result.verdict == case["expected_verdict"], (
        f"{case['id']}: verdict {result.verdict!r} != {case['expected_verdict']!r}"
    )
    assert result.reason_code == case["expected_reason_code"], (
        f"{case['id']}: reason {result.reason_code!r} != {case['expected_reason_code']!r}"
    )
    assert result.executable is case["expected_executable"], (
        f"{case['id']}: executable {result.executable!r} != {case['expected_executable']!r}"
    )
    for key, expected in case.get("expected_details", {}).items():
        assert result.details.get(key) == expected, (
            f"{case['id']}: details[{key!r}] {result.details.get(key)!r} != {expected!r}"
        )


@pytest.mark.parametrize("case", _cases_for("INV-D1"), ids=lambda case: case["id"])
def test_inv_d1_position_cap(case):
    """INV-D1 / REQ-D-002 (plus REQ-D-012/013 cases): cap and NAV handling."""
    _assert_case(case)


@pytest.mark.parametrize("case", _cases_for("INV-D2"), ids=lambda case: case["id"])
def test_inv_d2_forbidden_tickers(case):
    """INV-D2 / REQ-D-003 (plus REQ-D-012 cases): forbidden tickers and exits."""
    _assert_case(case)


@pytest.mark.parametrize("case", _cases_for("INV-D3"), ids=lambda case: case["id"])
def test_inv_d3_rating_domain(case):
    """INV-D3 / REQ-D-004: canonical 5-tier and Trader 3-tier rating domain."""
    _assert_case(case)


@pytest.mark.parametrize("case", _cases_for("INV-D4"), ids=lambda case: case["id"])
def test_inv_d4_review_terminal(case):
    """INV-D4 / REQ-D-005: REVIEW is terminal and non-executable."""
    _assert_case(case)


@pytest.mark.parametrize("case", _cases_for("INV-D5"), ids=lambda case: case["id"])
def test_inv_d5_fail_closed(case):
    """INV-D5 / REQ-D-006: missing/malformed fields BLOCK; modeled unknowns REVIEW."""
    _assert_case(case)


@pytest.mark.parametrize("case", _cases_for("INV-D6"), ids=lambda case: case["id"])
def test_inv_d6_dual_gate(case):
    """INV-D6 / REQ-D-007: Trader and final PM gates, including a missing gate."""
    _assert_case(case)


@pytest.mark.parametrize("case", _cases_for("INV-D7"), ids=lambda case: case["id"])
def test_inv_d7_authority(case):
    """INV-D7 / REQ-D-008: BLOCK authority, override rejection, monotonic merge."""
    _assert_case(case)


@pytest.mark.parametrize("case", _cases_for("INV-D8"), ids=lambda case: case["id"])
def test_inv_d8_unknown_position(case):
    """INV-D8 / REQ-D-009: unknown state is never treated as an empty position."""
    _assert_case(case)


def test_verdict_domain():
    """INV-D7 / REQ-D-008: the verdict domain is exactly PASS, REVIEW, BLOCK."""
    assert {verdict.value for verdict in Verdict} == {"PASS", "REVIEW", "BLOCK"}


def test_guard_result_shape_and_positive_executable():
    """REQ-D-001 / INV-D4: validate returns a GuardResult and PASS is executable."""
    result = validate(
        proposal={"ticker": "AAPL", "action": "Buy", "delta_quantity": 1, "price": 100},
        portfolio={"nav": 1000000, "currency": "USD", "positions": []},
        stage="pm",
    )
    assert isinstance(result, GuardResult)
    assert result.verdict == Verdict.PASS
    assert result.reason_code == "PASS"
    assert result.executable is True


def test_guard_purity_no_network_io(monkeypatch):
    """REQ-D-013 / INV-D1: the guard performs no network I/O."""

    def refuse(*args, **kwargs):
        raise AssertionError(f"guard attempted network I/O: {args[1:] or kwargs}")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)

    result = validate(
        proposal={"ticker": "AAPL", "action": "Buy", "delta_quantity": 1, "price": 100},
        portfolio={"nav": 1000000, "currency": "USD", "positions": []},
        stage="pm",
    )
    assert result.verdict == Verdict.PASS
