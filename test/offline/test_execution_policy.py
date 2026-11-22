"""Offline admission and accounting tests; no graph, model, or network."""

import pytest

from tradingagents import execution_policy as ep

pytestmark = pytest.mark.unit
FOLLOW_UP, FINAL_REVIEW = ep.FOLLOW_UP, ep.FINAL_REVIEW


def _count_if_allowed(decision, stage, calls):
    if decision.allowed:
        calls.append(stage)
    return decision


def _invoke(policy, stage, cost, calls):
    return _count_if_allowed(policy.admit(stage, cost), stage, calls)


def _balances(policy):
    """Available, reserved, final-review committed, spendable."""
    return (
        policy.available_units,
        policy.final_review_reserved_units,
        policy.final_review_committed_units,
        policy.spendable_units,
    )


def _assert_denial(decision, reason, scope):
    assert decision.allowed is False
    assert decision.reason == reason
    assert decision.scope == scope


@pytest.mark.parametrize(
    "units, expected_follow_ups, expected_review",
    [(3, 1, 1), (2, 0, 1), (1, 0, 0)],
)
def test_same_input_scales_with_budget(units, expected_follow_ups, expected_review):
    policy = ep.BudgetPolicy(available_units=units)
    calls = []
    reserve = policy.reserve_final_review(2)
    if units >= 2:
        assert reserve.allowed is True
        assert _balances(policy) == (units, 2, 0, units - 2)
    else:
        _assert_denial(
            reserve, ep.REASON_INSUFFICIENT_BUDGET_FINAL_REVIEW, ep.SCOPE_TERMINAL
        )
        assert _balances(policy) == (1, 0, 0, 1)

    follow_ups = [_invoke(policy, FOLLOW_UP, 1, calls) for _ in range(3)]
    review = _invoke(policy, FINAL_REVIEW, 2, calls)
    assert calls.count(FOLLOW_UP) == expected_follow_ups
    assert calls.count(FINAL_REVIEW) == expected_review
    if expected_review:
        assert review.allowed is True
        assert _balances(policy) == (0, 0, 2, 0)
        assert all(d.allowed is True for d in follow_ups[:expected_follow_ups])
        for denied in follow_ups[expected_follow_ups:]:
            _assert_denial(
                denied, ep.REASON_INSUFFICIENT_BUDGET_FOLLOW_UP, ep.SCOPE_RESEARCH
            )
    else:
        for decision in (*follow_ups, review):
            _assert_denial(
                decision, ep.REASON_INSUFFICIENT_BUDGET_FINAL_REVIEW, ep.SCOPE_TERMINAL
            )
        assert _balances(policy) == (1, 0, 0, 1)


def test_spendable_reserved_and_committed_are_deducted_once():
    policy = ep.BudgetPolicy(available_units=4)
    calls = []
    assert _balances(policy) == (4, 0, 0, 4)
    assert policy.reserve_final_review(2).allowed is True
    assert _balances(policy) == (4, 2, 0, 2)
    assert _invoke(policy, FOLLOW_UP, 1, calls).allowed is True
    assert _balances(policy) == (3, 2, 0, 1)
    assert _invoke(policy, FINAL_REVIEW, 2, calls).allowed is True
    assert _balances(policy) == (1, 0, 2, 1)
    policy.record_usage(FINAL_REVIEW, 1)
    assert _balances(policy) == (2, 0, 0, 2)


def test_reservation_is_reported_separately_from_usage():
    policy = ep.BudgetPolicy(available_units=3)
    calls = []
    assert policy.reserve_final_review(2).allowed is True
    assert _invoke(policy, FOLLOW_UP, 1, calls).allowed is True
    assert _invoke(policy, FINAL_REVIEW, 2, calls).allowed is True
    assert _balances(policy) == (0, 0, 2, 0)
    policy.record_usage(FINAL_REVIEW, 1)
    usage = policy.usage_for(FINAL_REVIEW)
    assert (usage.status, usage.reported_units) == (ep.REPORTED, 1)
    assert _balances(policy) == (1, 0, 0, 1)
    probe = _invoke(policy, FOLLOW_UP, 1, calls)
    assert probe.allowed is True
    assert probe.scope == ep.SCOPE_POLICY
    assert _balances(policy) == (0, 0, 0, 0)


def test_missing_usage_is_unknown_not_zero():
    policy = ep.BudgetPolicy(available_units=3)
    calls = []
    assert policy.reserve_final_review(2).allowed is True
    assert _invoke(policy, FINAL_REVIEW, 2, calls).allowed is True
    assert _balances(policy) == (1, 0, 2, 1)
    policy.record_usage(FINAL_REVIEW, None)
    usage = policy.usage_for(FINAL_REVIEW)
    assert (usage.status, usage.reported_units) == (ep.UNKNOWN, None)
    assert _balances(policy) == (1, 0, 2, 1)


def test_denied_call_preserves_reservation_and_is_not_invoked():
    policy = ep.BudgetPolicy(available_units=2)
    calls = []
    assert policy.reserve_final_review(2).allowed is True
    denied = _invoke(policy, FOLLOW_UP, 1, calls)
    _assert_denial(
        denied, ep.REASON_INSUFFICIENT_BUDGET_FOLLOW_UP, ep.SCOPE_RESEARCH
    )
    assert calls == []
    assert _balances(policy) == (2, 2, 0, 0)
    usage = policy.usage_for(FOLLOW_UP)
    assert (usage.status, usage.reported_units) == (ep.NOT_INVOKED, None)


def test_stage_never_admitted_reports_not_invoked():
    policy = ep.BudgetPolicy(available_units=2)
    usage = policy.usage_for(FOLLOW_UP)
    assert (usage.status, usage.reported_units) == (ep.NOT_INVOKED, None)


@pytest.mark.parametrize(
    "reported, status, before, admitted, expected_follow_ups",
    [(1, ep.REPORTED, 1, True, 2), (None, ep.UNKNOWN, 0, False, 1)],
    ids=["verified-remainder", "missing-usage"],
)
def test_remainder_probe(reported, status, before, admitted, expected_follow_ups):
    policy = ep.BudgetPolicy(available_units=4)
    calls = []
    assert policy.reserve_final_review(2).allowed is True
    assert _invoke(policy, FOLLOW_UP, 2, calls).allowed is True
    assert _balances(policy) == (2, 2, 0, 0)
    policy.record_usage(FOLLOW_UP, reported)
    usage = policy.usage_for(FOLLOW_UP)
    assert (usage.status, usage.reported_units) == (status, reported)

    assert _balances(policy) == (2 + before, 2, 0, before)
    probe = _invoke(policy, FOLLOW_UP, 1, calls)
    assert _balances(policy) == (2, 2, 0, 0)
    assert probe.allowed is admitted
    if admitted:
        assert probe.reason == ""
    else:
        _assert_denial(
            probe, ep.REASON_INSUFFICIENT_BUDGET_FOLLOW_UP, ep.SCOPE_RESEARCH
        )
    assert calls.count(FOLLOW_UP) == expected_follow_ups
    assert _invoke(policy, FINAL_REVIEW, 2, calls).allowed is True
    assert calls.count(FINAL_REVIEW) == 1
    assert _balances(policy) == (0, 0, 2, 0)


def test_t_p1_failed_reservation_locks_the_terminal_state():
    policy = ep.BudgetPolicy(available_units=1)
    calls = []
    reason = ep.REASON_INSUFFICIENT_BUDGET_FINAL_REVIEW
    _assert_denial(policy.reserve_final_review(2), reason, ep.SCOPE_TERMINAL)
    assert _balances(policy) == (1, 0, 0, 1)

    follow_up = policy.admit(FOLLOW_UP, 1)
    review = policy.admit(FINAL_REVIEW, 2)
    _count_if_allowed(follow_up, FOLLOW_UP, calls)
    _count_if_allowed(review, FINAL_REVIEW, calls)

    assert follow_up.allowed is False, "a locked policy must refuse follow-ups"
    assert review.allowed is False, "a locked policy must refuse final review"
    for decision in (follow_up, review):
        _assert_denial(decision, reason, ep.SCOPE_TERMINAL)
    assert calls == []
    assert _balances(policy) == (1, 0, 0, 1)


def test_t_p2_a_commitment_can_be_used_only_once():
    policy = ep.BudgetPolicy(available_units=2)
    calls = []
    assert policy.reserve_final_review(2).allowed is True
    assert _balances(policy) == (2, 2, 0, 0)
    assert _invoke(policy, FINAL_REVIEW, 2, calls).allowed is True
    assert _balances(policy) == (0, 0, 2, 0)

    policy.record_usage(FINAL_REVIEW, 1)
    usage = policy.usage_for(FINAL_REVIEW)
    assert (usage.status, usage.reported_units) == (ep.REPORTED, 1)
    assert _balances(policy) == (1, 0, 0, 1)

    second = policy.admit(FINAL_REVIEW, 2)
    _count_if_allowed(second, FINAL_REVIEW, calls)
    assert second.allowed is False, "the final review must not run twice"
    assert second.reason == ep.REASON_RESERVATION_ALREADY_COMMITTED
    assert second.scope == ep.SCOPE_TERMINAL
    assert calls == [FINAL_REVIEW]
    assert _balances(policy) == (1, 0, 0, 1)

    # One unit is still spendable, so only the terminal lock should refuse it.
    follow_up = policy.admit(FOLLOW_UP, 1)
    _count_if_allowed(follow_up, FOLLOW_UP, calls)
    assert follow_up.allowed is False, "terminal duplicate denial must lock follow-ups"
    assert follow_up.reason == second.reason
    assert follow_up.scope == second.scope
    assert calls == [FINAL_REVIEW]
    assert _balances(policy) == (1, 0, 0, 1)


def test_t_p3_overspend_is_recorded_truthfully_and_releases_no_credit():
    policy = ep.BudgetPolicy(available_units=2)
    calls = []
    assert policy.reserve_final_review(2).allowed is True
    assert _invoke(policy, FINAL_REVIEW, 2, calls).allowed is True
    assert _balances(policy) == (0, 0, 2, 0)

    policy.record_usage(FINAL_REVIEW, 3)
    usage = policy.usage_for(FINAL_REVIEW)
    assert (usage.status, usage.reported_units) == (ep.REPORTED, 3)
    assert policy.overspend is True
    assert _balances(policy) == (0, 0, 0, 0)

    probe = policy.admit(FOLLOW_UP, 1)
    _count_if_allowed(probe, FOLLOW_UP, calls)
    _assert_denial(
        probe, ep.REASON_INSUFFICIENT_BUDGET_FOLLOW_UP, ep.SCOPE_RESEARCH
    )
    assert calls == [FINAL_REVIEW]
    assert _balances(policy) == (0, 0, 0, 0)
