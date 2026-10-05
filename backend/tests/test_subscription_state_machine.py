import pytest

from app.models.enums import SubscriptionStatus as S
from app.services.subscription_state_machine import (
    ALLOWED_TRANSITIONS,
    IllegalTransitionError,
    assert_transition,
    can_transition,
)

LEGAL = [
    (S.TRIALING, S.ACTIVE),
    (S.TRIALING, S.CANCELLED),
    (S.ACTIVE, S.PAST_DUE),
    (S.ACTIVE, S.CANCELLED),
    (S.PAST_DUE, S.ACTIVE),
    (S.PAST_DUE, S.SUSPENDED),
    (S.PAST_DUE, S.CANCELLED),
    (S.SUSPENDED, S.ACTIVE),
    (S.SUSPENDED, S.CANCELLED),
]


@pytest.mark.parametrize("current,target", LEGAL)
def test_legal_transitions_are_allowed(current, target):
    assert can_transition(current, target)
    assert_transition(current, target)  # must not raise


ILLEGAL = [
    (S.TRIALING, S.PAST_DUE),
    (S.TRIALING, S.SUSPENDED),
    (S.ACTIVE, S.TRIALING),
    (S.ACTIVE, S.SUSPENDED),  # must go through past_due first
    (S.SUSPENDED, S.PAST_DUE),
    (S.CANCELLED, S.ACTIVE),  # terminal
    (S.CANCELLED, S.TRIALING),
]


@pytest.mark.parametrize("current,target", ILLEGAL)
def test_illegal_transitions_raise(current, target):
    assert not can_transition(current, target)
    with pytest.raises(IllegalTransitionError):
        assert_transition(current, target)


def test_same_state_is_not_a_transition():
    for status in S:
        assert not can_transition(status, status)


def test_cancelled_is_terminal():
    assert ALLOWED_TRANSITIONS[S.CANCELLED] == frozenset()


def test_every_status_has_a_rule():
    assert set(ALLOWED_TRANSITIONS) == set(S)
