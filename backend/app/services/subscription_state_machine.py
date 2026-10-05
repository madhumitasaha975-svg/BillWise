"""Subscription lifecycle rules. Pure Python: no database, no FastAPI.

    trialing --> active --> past_due --> suspended
        |           |          |  ^          |
        |           |          |  +--(paid)--+--> active (reactivated)
        +-----------+----------+-----------------> cancelled (terminal)
"""

from app.models.enums import SubscriptionStatus as S

ALLOWED_TRANSITIONS: dict[S, frozenset[S]] = {
    S.TRIALING: frozenset({S.ACTIVE, S.CANCELLED}),
    S.ACTIVE: frozenset({S.PAST_DUE, S.CANCELLED}),
    S.PAST_DUE: frozenset({S.ACTIVE, S.SUSPENDED, S.CANCELLED}),  # ACTIVE = payment recovered
    S.SUSPENDED: frozenset({S.ACTIVE, S.CANCELLED}),  # ACTIVE = reactivated after payment
    S.CANCELLED: frozenset(),  # terminal: nothing leaves cancelled
}


class IllegalTransitionError(Exception):
    def __init__(self, current: S, target: S):
        self.current = current
        self.target = target
        super().__init__(f"Illegal subscription transition: {current.value} -> {target.value}")


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def assert_transition(current: S, target: S) -> None:
    """Raise IllegalTransitionError unless current -> target is allowed."""
    if not can_transition(current, target):
        raise IllegalTransitionError(current, target)
