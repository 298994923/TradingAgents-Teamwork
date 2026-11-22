"""Standalone admission and usage accounting for a workflow run."""

from collections import deque
from dataclasses import dataclass

FOLLOW_UP = "follow_up"
FINAL_REVIEW = "final_review"

SCOPE_POLICY = "policy"
SCOPE_RESEARCH = "research"
SCOPE_TERMINAL = "terminal"

REASON_INSUFFICIENT_BUDGET_FINAL_REVIEW = "INSUFFICIENT_BUDGET_FINAL_REVIEW"
REASON_INSUFFICIENT_BUDGET_FOLLOW_UP = "INSUFFICIENT_BUDGET_FOLLOW_UP"
REASON_RESERVATION_ALREADY_COMMITTED = "RESERVATION_ALREADY_COMMITTED"

REPORTED = "reported"
UNKNOWN = "unknown"
NOT_INVOKED = "not_invoked"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    scope: str
    stage: str = ""


@dataclass(frozen=True)
class Usage:
    stage: str
    status: str
    reported_units: int | None


def _validate_units(units: int, name: str) -> None:
    if isinstance(units, bool) or not isinstance(units, int) or units < 0:
        raise ValueError(f"{name} must be a non-negative integer")


class BudgetPolicy:
    """Ring-fence final review and charge commitments before calls run.

    The caller reports usage once per admission, in admission order within
    each stage, because the interface identifies reports by stage, not call ID.
    """

    def __init__(self, available_units: int) -> None:
        _validate_units(available_units, "available_units")
        self._net_balance = available_units
        self._reserved: int | None = None
        self._final_review_used = False
        self._final_review_committed = 0
        self._terminal_reason: str | None = None
        self._overspend = False
        self._pending: dict[str, deque[int]] = {FOLLOW_UP: deque(), FINAL_REVIEW: deque()}
        self._usage: dict[str, Usage] = {}

    @property
    def available_units(self) -> int:
        return max(0, self._net_balance)

    @property
    def final_review_reserved_units(self) -> int:
        return min(self._reserved or 0, self.available_units)

    @property
    def final_review_committed_units(self) -> int:
        return self._final_review_committed

    @property
    def spendable_units(self) -> int:
        return self.available_units - self.final_review_reserved_units

    @property
    def overspend(self) -> bool:
        return self._overspend

    def _deny_terminal(self, reason: str, stage: str) -> Decision:
        if self._terminal_reason is None:
            self._terminal_reason = reason
        return Decision(False, self._terminal_reason, SCOPE_TERMINAL, stage)

    def reserve_final_review(self, units: int) -> Decision:
        """Protect at least `units` until the single final-review admission."""
        if self._terminal_reason is not None:
            return self._deny_terminal(self._terminal_reason, FINAL_REVIEW)
        _validate_units(units, "units")
        if self._final_review_used:
            return self._deny_terminal(REASON_RESERVATION_ALREADY_COMMITTED, FINAL_REVIEW)
        if units > self.available_units:
            return self._deny_terminal(REASON_INSUFFICIENT_BUDGET_FINAL_REVIEW, FINAL_REVIEW)
        self._reserved = max(self._reserved or 0, units)
        return Decision(True, "", SCOPE_POLICY, FINAL_REVIEW)

    def admit(self, stage: str, cost: int) -> Decision:
        """Decide whether a call may run and deduct its cost if admitted."""
        if self._terminal_reason is not None:
            return self._deny_terminal(self._terminal_reason, stage)
        if stage not in self._pending:
            raise ValueError(f"unknown budget stage: {stage!r}")
        _validate_units(cost, "cost")

        if stage == FINAL_REVIEW:
            if self._final_review_used:
                return self._deny_terminal(REASON_RESERVATION_ALREADY_COMMITTED, stage)
            if self._reserved is None or cost > self.final_review_reserved_units:
                return self._deny_terminal(REASON_INSUFFICIENT_BUDGET_FINAL_REVIEW, stage)
            self._reserved = None
            self._final_review_used = True
            self._final_review_committed = cost
        elif cost > self.spendable_units:
            return Decision(False, REASON_INSUFFICIENT_BUDGET_FOLLOW_UP, SCOPE_RESEARCH, stage)

        self._net_balance -= cost
        self._pending[stage].append(cost)
        return Decision(True, "", SCOPE_POLICY, stage)

    def record_usage(self, stage: str, reported_units: int | None) -> None:
        """Settle the oldest unreported admission for `stage`."""
        pending = self._pending.get(stage)
        if not pending:
            raise ValueError(f"no pending admission for stage: {stage!r}")
        if reported_units is not None:
            _validate_units(reported_units, "reported_units")
        committed = pending.popleft()

        if reported_units is None:
            self._usage[stage] = Usage(stage, UNKNOWN, None)
            return

        self._usage[stage] = Usage(stage, REPORTED, reported_units)
        if stage == FINAL_REVIEW:
            self._final_review_committed = 0
        # Carry any deficit internally so later refunds cannot create phantom capacity.
        self._net_balance += committed - reported_units
        if reported_units > committed:
            self._overspend = True

    def usage_for(self, stage: str) -> Usage:
        """Return the latest recorded usage, or the status before a report."""
        if stage in self._usage:
            return self._usage[stage]
        status = UNKNOWN if self._pending.get(stage) else NOT_INVOKED
        return Usage(stage, status, None)
