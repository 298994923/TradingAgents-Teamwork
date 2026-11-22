"""Deterministic safety guard for D's decision checkpoints.

The AI agents are advisory. This module is authoritative and returns only
``PASS``, ``REVIEW``, or ``BLOCK``. It performs no network, LLM, or order I/O.

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

Invariants: INV-D1..INV-D8. Requirements: REQ-D-002..REQ-D-013.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from tradingagents.dataflows.symbols import normalize_symbol


class Verdict(StrEnum):
    """Deterministic guard verdict. Severity: BLOCK > REVIEW > PASS."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


_VERDICT_RANK = {Verdict.PASS: 0, Verdict.REVIEW: 1, Verdict.BLOCK: 2}


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

_DEFAULT_CAP_PERCENT = Decimal("10")
_RELATIVE_EPSILON = Decimal("1e-9")
_DEFAULT_FORBIDDEN = frozenset({"DEMO-BAN"})
_FIVE_TIER = frozenset({"buy", "overweight", "hold", "underweight", "sell"})
_THREE_TIER = frozenset({"buy", "hold", "sell"})
_EXPOSURE_INCREASING = frozenset({"buy", "add", "short"})
_ALLOWED_EXITS = frozenset({"reduce", "exit"})
_MISSING = object()


class _GuardFailure(Exception):
    """Internal control flow for a terminal guard verdict."""

    def __init__(
        self,
        verdict: Verdict,
        reason_code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(reason_code)
        self.verdict = verdict
        self.reason_code = reason_code
        self.details = details or {}


def _checkpoint(stage: object) -> str:
    return stage if isinstance(stage, str) and stage else "unknown"


def _result(
    verdict: Verdict,
    reason_code: str,
    stage: object,
    details: dict[str, Any] | None = None,
) -> GuardResult:
    return GuardResult(
        verdict=verdict,
        reason_code=reason_code,
        checkpoint=_checkpoint(stage),
        executable=verdict == Verdict.PASS,
        details=details or {},
    )


def _merge_verdicts(*verdicts: Verdict) -> Verdict:
    """INV-D7: maximum-severity, monotonic merge (BLOCK > REVIEW > PASS)."""
    return max(verdicts, key=lambda verdict: _VERDICT_RANK[verdict])


def _to_decimal(value: object) -> Decimal:
    """Parse a finite Decimal without ever falling back to float arithmetic."""
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric quantity")
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, int):
        parsed = Decimal(value)
    elif isinstance(value, float):
        parsed = Decimal(str(value))
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("empty numeric string")
        parsed = Decimal(text)
    else:
        raise TypeError(f"unsupported numeric type {type(value).__name__}")
    if not parsed.is_finite():
        raise ValueError("non-finite numeric value")
    return parsed


def _resolve_config(config: object) -> tuple[Decimal, frozenset[str]]:
    """REQ-D-012: validate guard configuration before any decision work."""
    if config is None:
        return _DEFAULT_CAP_PERCENT / Decimal("100"), _DEFAULT_FORBIDDEN
    if not isinstance(config, dict):
        raise _GuardFailure(Verdict.BLOCK, "CONFIG_INVALID", {"field": "config"})

    cap_percent = _DEFAULT_CAP_PERCENT
    if "position_cap_percent" in config:
        try:
            cap_percent = _to_decimal(config["position_cap_percent"])
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise _GuardFailure(
                Verdict.BLOCK, "CONFIG_INVALID", {"field": "position_cap_percent"}
            ) from exc
        if cap_percent <= 0 or cap_percent > 100:
            raise _GuardFailure(
                Verdict.BLOCK, "CONFIG_INVALID", {"field": "position_cap_percent"}
            )

    forbidden = _DEFAULT_FORBIDDEN
    if "forbidden_tickers" in config:
        raw = config["forbidden_tickers"]
        if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple, set, frozenset)):
            raise _GuardFailure(
                Verdict.BLOCK, "CONFIG_INVALID", {"field": "forbidden_tickers"}
            )
        entries = set()
        for entry in raw:
            if not isinstance(entry, str) or not entry.strip():
                raise _GuardFailure(
                    Verdict.BLOCK, "CONFIG_INVALID", {"field": "forbidden_tickers"}
                )
            entries.add(normalize_symbol(entry))
        forbidden = frozenset(entries)

    return cap_percent / Decimal("100"), forbidden


def _normalize_ticker(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise _GuardFailure(Verdict.BLOCK, "MALFORMED_FIELD", {"field": "ticker"})
    return normalize_symbol(raw)


def _required_decimal(proposal: dict[str, Any], names: tuple[str, ...]) -> Decimal:
    for name in names:
        if name in proposal:
            try:
                return _to_decimal(proposal[name])
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise _GuardFailure(
                    Verdict.BLOCK, "MALFORMED_FIELD", {"field": name}
                ) from exc
    raise _GuardFailure(Verdict.BLOCK, "MISSING_FIELD", {"field": names[0]})


def _portfolio_decimal(value: object, field_name: str) -> Decimal:
    try:
        return _to_decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise _GuardFailure(
            Verdict.BLOCK, "MALFORMED_PORTFOLIO", {"field": field_name}
        ) from exc


def _resolve_portfolio(
    portfolio: object,
    ticker: str,
) -> tuple[Decimal | None, str | None, Decimal, frozenset[str]]:
    """INV-D8: preserve absent, flat, unknown, and malformed states distinctly."""
    if portfolio is ABSENT:
        raise _GuardFailure(
            Verdict.REVIEW, "POSITION_UNKNOWN", {"field": "portfolio"}
        )
    if not isinstance(portfolio, dict):
        raise _GuardFailure(
            Verdict.BLOCK, "MALFORMED_PORTFOLIO", {"field": "portfolio"}
        )

    positions = portfolio.get("positions", _MISSING)
    if positions is _MISSING or not isinstance(positions, list):
        raise _GuardFailure(
            Verdict.BLOCK, "MALFORMED_PORTFOLIO", {"field": "positions"}
        )

    held = Decimal("0")
    position_currencies: set[str] = set()
    for index, position in enumerate(positions):
        if not isinstance(position, dict):
            raise _GuardFailure(
                Verdict.BLOCK, "MALFORMED_PORTFOLIO", {"field": f"positions[{index}]"}
            )

        raw_ticker = position.get("ticker", _MISSING)
        if raw_ticker is _MISSING:
            raise _GuardFailure(
                Verdict.BLOCK, "MALFORMED_PORTFOLIO", {"field": f"positions[{index}].ticker"}
            )
        if raw_ticker is None:
            raise _GuardFailure(
                Verdict.REVIEW, "POSITION_UNKNOWN", {"field": f"positions[{index}].ticker"}
            )
        if not isinstance(raw_ticker, str) or not raw_ticker.strip():
            raise _GuardFailure(
                Verdict.BLOCK, "MALFORMED_PORTFOLIO", {"field": f"positions[{index}].ticker"}
            )

        raw_quantity = position.get("quantity", _MISSING)
        if raw_quantity is _MISSING:
            raise _GuardFailure(
                Verdict.BLOCK, "MALFORMED_PORTFOLIO", {"field": f"positions[{index}].quantity"}
            )
        if raw_quantity is None:
            raise _GuardFailure(
                Verdict.REVIEW, "POSITION_UNKNOWN", {"field": f"positions[{index}].quantity"}
            )
        quantity = _portfolio_decimal(raw_quantity, f"positions[{index}].quantity")

        if "price" in position:
            raw_price = position["price"]
            if raw_price is None:
                raise _GuardFailure(
                    Verdict.REVIEW, "POSITION_UNKNOWN", {"field": f"positions[{index}].price"}
                )
            _portfolio_decimal(raw_price, f"positions[{index}].price")

        if "currency" in position:
            raw_currency = position["currency"]
            if raw_currency is None:
                raise _GuardFailure(
                    Verdict.REVIEW,
                    "POSITION_UNKNOWN",
                    {"field": f"positions[{index}].currency"},
                )
            if not isinstance(raw_currency, str):
                raise _GuardFailure(
                    Verdict.BLOCK,
                    "MALFORMED_PORTFOLIO",
                    {"field": f"positions[{index}].currency"},
                )
            position_currencies.add(raw_currency.strip().upper())

        if normalize_symbol(raw_ticker) == ticker:
            held += quantity

    raw_nav = portfolio.get("nav", _MISSING)
    nav = (
        None
        if raw_nav is _MISSING or raw_nav is None
        else _portfolio_decimal(raw_nav, "nav")
    )

    raw_portfolio_currency = portfolio.get("currency")
    if raw_portfolio_currency is not None and not isinstance(raw_portfolio_currency, str):
        raise _GuardFailure(
            Verdict.BLOCK, "MALFORMED_PORTFOLIO", {"field": "currency"}
        )
    portfolio_currency = (
        raw_portfolio_currency.strip().upper()
        if isinstance(raw_portfolio_currency, str) and raw_portfolio_currency.strip()
        else None
    )

    return nav, portfolio_currency, held, frozenset(position_currencies)


def _proposal_currency(proposal: dict[str, Any]) -> str | None:
    if "currency" not in proposal or proposal["currency"] is None:
        return None
    raw = proposal["currency"]
    if not isinstance(raw, str) or not raw.strip():
        raise _GuardFailure(Verdict.BLOCK, "MALFORMED_FIELD", {"field": "currency"})
    return raw.strip().upper()


def _validate_rating(value: object, stage: str) -> None:
    """INV-D3: canonical tier domains, case/whitespace normalized, no aliases."""
    if not isinstance(value, str):
        raise _GuardFailure(Verdict.BLOCK, "INVALID_RATING", {"field": _rating_field(stage)})
    normalized = value.strip().lower()
    if normalized == "review":
        raise _GuardFailure(
            Verdict.REVIEW, "RATING_UNREADABLE", {"field": _rating_field(stage)}
        )
    allowed = _THREE_TIER if stage == "trader" else _FIVE_TIER
    if normalized not in allowed:
        raise _GuardFailure(
            Verdict.BLOCK, "INVALID_RATING", {"field": _rating_field(stage)}
        )


def _rating_field(stage: str) -> str:
    return "action" if stage == "trader" else "rating"


def _coerce_prior_verdict(value: object) -> Verdict | None:
    if value is None:
        return None
    if isinstance(value, Verdict):
        return value
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in Verdict.__members__:
            return Verdict[normalized]
    raise _GuardFailure(
        Verdict.BLOCK, "MALFORMED_FIELD", {"field": "prior_verdict"}
    )


def _validate_cap(
    *,
    proposal: dict[str, Any],
    ticker: str,
    price: Decimal,
    proposed_quantity: Decimal,
    portfolio: object,
    stage: str,
    cap_fraction: Decimal,
) -> None:
    """INV-D1: gross absolute post-trade exposure at most 10% of NAV."""
    nav, portfolio_currency, held, position_currencies = _resolve_portfolio(
        portfolio, ticker
    )

    proposal_currency = _proposal_currency(proposal)
    currencies = set(position_currencies)
    if portfolio_currency:
        currencies.add(portfolio_currency)
    if proposal_currency and portfolio_currency and proposal_currency != portfolio_currency:
        raise _GuardFailure(Verdict.REVIEW, "CURRENCY_MISMATCH")
    if len(currencies) > 1:
        raise _GuardFailure(Verdict.REVIEW, "CURRENCY_MISMATCH")
    if (
        proposal_currency
        and portfolio_currency is None
        and position_currencies
        and proposal_currency not in position_currencies
    ):
        raise _GuardFailure(Verdict.REVIEW, "CURRENCY_MISMATCH")

    if nav is None:
        raise _GuardFailure(Verdict.REVIEW, "NAV_UNKNOWN", {"field": "nav"})

    post_trade_quantity = held + proposed_quantity
    exposure = abs(post_trade_quantity * price)
    allowed_cap = nav * cap_fraction
    tolerance = allowed_cap * _RELATIVE_EPSILON

    if exposure > allowed_cap + tolerance:
        raise _GuardFailure(
            Verdict.BLOCK,
            "CAP_EXCEEDED",
            {
                "observed_exposure": exposure,
                "allowed_cap": allowed_cap,
                "checkpoint": stage,
                "post_trade_quantity": post_trade_quantity,
                "price": price,
            },
        )


def _validate_forbidden(
    *,
    ticker: str,
    proposal: dict[str, Any],
    forbidden: frozenset[str],
) -> str:
    """INV-D2: block exposure increases; allow reductions and exits."""
    if ticker not in forbidden:
        return "PASS"

    raw_action = proposal.get("action")
    action = raw_action.strip().lower() if isinstance(raw_action, str) else None
    if action in _ALLOWED_EXITS:
        return "ALLOWED_EXIT"
    if action in _EXPOSURE_INCREASING:
        raise _GuardFailure(
            Verdict.BLOCK,
            "FORBIDDEN_TICKER",
            {"ticker": ticker, "action": action},
        )
    raise _GuardFailure(
        Verdict.BLOCK,
        "FORBIDDEN_TICKER",
        {"ticker": ticker, "action": action},
    )


def _validate_impl(
    proposal: dict[str, Any],
    portfolio: object,
    stage: str | None,
    prior_verdict: Verdict | str | None,
    llm_text: str | None,
    config: dict[str, Any] | None,
) -> GuardResult:
    # REQ-D-012: configuration fails closed before any decision work.
    cap_fraction, forbidden = _resolve_config(config)

    # INV-D6: both the Trader gate and the final PM gate must run.
    if stage not in ("trader", "pm"):
        raise _GuardFailure(Verdict.BLOCK, "GATE_MISSING", {"stage": stage})

    # INV-D7: authority is monotonic; LLM text can never lower a BLOCK.
    prior = _coerce_prior_verdict(prior_verdict)
    if prior == Verdict.BLOCK:
        if llm_text is not None:
            raise _GuardFailure(
                Verdict.BLOCK,
                "OVERRIDE_REJECTED",
                {"override_rejected": True, "prior_verdict": prior.value},
            )
        raise _GuardFailure(
            Verdict.BLOCK,
            "PRIOR_VERDICT_RETAINED",
            {"prior_verdict": prior.value},
        )
    if prior == Verdict.REVIEW:
        # INV-D4: REVIEW is terminal whether raised now or carried forward.
        raise _GuardFailure(
            Verdict.REVIEW,
            "REVIEW_TERMINAL",
            {"prior_verdict": prior.value},
        )

    # INV-D5: required fields fail closed; malformed values never become PASS.
    if not isinstance(proposal, dict):
        raise _GuardFailure(Verdict.BLOCK, "MALFORMED_FIELD", {"field": "proposal"})

    if "ticker" not in proposal:
        raise _GuardFailure(Verdict.BLOCK, "MISSING_FIELD", {"field": "ticker"})
    ticker = _normalize_ticker(proposal["ticker"])

    if stage == "trader" and "action" not in proposal:
        raise _GuardFailure(Verdict.BLOCK, "MISSING_FIELD", {"field": "action"})
    if stage == "pm" and "rating" not in proposal and "action" not in proposal:
        raise _GuardFailure(Verdict.BLOCK, "MISSING_FIELD", {"field": "rating"})

    if "price" not in proposal:
        raise _GuardFailure(Verdict.BLOCK, "MISSING_FIELD", {"field": "price"})
    price = _required_decimal(proposal, ("price",))

    proposed_quantity = _required_decimal(proposal, ("quantity", "delta_quantity"))

    # INV-D3: validate the decision domain appropriate to this checkpoint.
    if stage == "trader":
        _validate_rating(proposal["action"], stage)
    elif "rating" in proposal:
        _validate_rating(proposal["rating"], stage)

    # INV-D1: resolve the book and enforce the cap before the forbidden check,
    # so an oversized or unknown position cannot slip through later.
    _validate_cap(
        proposal=proposal,
        ticker=ticker,
        price=price,
        proposed_quantity=proposed_quantity,
        portfolio=portfolio,
        stage=stage,
        cap_fraction=cap_fraction,
    )

    # INV-D2: forbidden-list check after the cap and rating checks.
    reason_code = _validate_forbidden(
        ticker=ticker,
        proposal=proposal,
        forbidden=forbidden,
    )

    return _result(Verdict.PASS, reason_code, stage)


def validate(
    proposal: dict[str, Any],
    portfolio: object = ABSENT,
    stage: str | None = "pm",
    prior_verdict: Verdict | str | None = None,
    llm_text: str | None = None,
    config: dict[str, Any] | None = None,
) -> GuardResult:
    """Run the deterministic guard at a Trader or final PM checkpoint.

    INV-D1..INV-D8, REQ-D-001..REQ-D-013. Pure and deterministic: no network,
    LLM, or order I/O. ``executable`` is True only for a final PASS.
    """
    try:
        return _validate_impl(
            proposal=proposal,
            portfolio=portfolio,
            stage=stage,
            prior_verdict=prior_verdict,
            llm_text=llm_text,
            config=config,
        )
    except _GuardFailure as failure:
        return _result(
            failure.verdict,
            failure.reason_code,
            stage,
            failure.details,
        )
