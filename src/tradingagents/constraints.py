"""Deterministic safety guard for D's decision checkpoints.

NAIVE STUB - to be replaced after test approval.

This module intentionally implements no safety logic yet. ``validate`` always
returns ``PASS`` so the offline test suite can run and fail for the right reason
before the real checks are written.

Public API (D's interface contract):

    validate(proposal, portfolio=ABSENT, stage="pm", prior_verdict=None,
             llm_text=None, config=None) -> GuardResult

Stable reason codes (one per distinct failure cause):

    PASS                     no violation
    CAP_EXCEEDED             post-trade gross absolute exposure above 10% NAV
    FORBIDDEN_TICKER         exposure-increasing action on the forbidden list
    ALLOWED_EXIT             reduction or exit on a forbidden ticker (PASS)
    INVALID_RATING           rating/action outside the allowed tier domain
    RATING_UNREADABLE        explicit non-tradeable REVIEW rating sentinel
    REVIEW_TERMINAL          terminal, non-executable REVIEW disposition
    REVIEW_EXECUTION_LEAK    REVIEW tried to enter the execution path
    MISSING_FIELD            required field absent
    MALFORMED_FIELD          required field present but unparsable/wrong type
    KNOWN_UNKNOWN            explicitly modeled unknown state
    GATE_MISSING             Trader or final PM gate did not run
    DUAL_GATE_FAILURE        merged dual-gate record retained a failure
    OVERRIDE_REJECTED        LLM text or later check tried to lower a BLOCK
    PRIOR_VERDICT_RETAINED   monotonic merge kept a higher prior verdict
    POSITION_UNKNOWN         position/ticker/quantity explicitly unknown
    NAV_UNKNOWN              NAV required by the cap is explicitly unknown
    MALFORMED_PORTFOLIO      portfolio payload could not be parsed
    CURRENCY_MISMATCH        portfolio/proposal currencies do not match
    CONFIG_INVALID           guard configuration failed validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    """Deterministic guard verdict. Severity: BLOCK > REVIEW > PASS."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class GuardResult:
    """A single guard verdict with its reason code and audit context."""

    verdict: Verdict
    reason_code: str
    checkpoint: str
    executable: bool
    details: dict[str, Any] = field(default_factory=dict)


class _Absent:
    """Sentinel distinguishing an absent portfolio from an explicit null."""

    def __repr__(self) -> str:
        return "ABSENT"


ABSENT = _Absent()


def validate(
    proposal: dict[str, Any],
    portfolio: object = ABSENT,
    stage: str | None = "pm",
    prior_verdict: Verdict | str | None = None,
    llm_text: str | None = None,
    config: dict[str, Any] | None = None,
) -> GuardResult:
    """NAIVE STUB - to be replaced after test approval.

    Always returns PASS. Real checks for INV-D1..INV-D8 are deliberately not
    implemented yet.
    """
    del proposal, portfolio, prior_verdict, llm_text, config
    checkpoint = stage if isinstance(stage, str) else "unknown"
    return GuardResult(
        verdict=Verdict.PASS,
        reason_code="PASS",
        checkpoint=checkpoint,
        executable=True,
        details={},
    )
