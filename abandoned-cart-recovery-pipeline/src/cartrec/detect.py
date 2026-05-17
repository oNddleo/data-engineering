"""Identify abandoned-cart sessions.

A session counts as abandoned when:

* It has **at least one ``ADD_TO_CART``** (the buyer expressed
  intent), and
* It did **not** complete checkout, and
* The net cart value is **above** ``min_cart_vnd`` (default 50,000 VND
  — VN marketplaces typically don't run recovery for ≤ ₫50k carts
  since campaign cost > expected revenue).

Sessions that **explicitly abandoned** (the buyer hit
``ABANDON_CHECKOUT`` — closed the checkout drawer) are still counted
— most CRM teams chase them as the highest-intent cohort. Production
callers can split into two classes (explicit vs implicit timeout)
via the returned :class:`AbandonedSession`'s ``reason`` field.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cartrec.schema import Session


class AbandonReason(str, Enum):
    """Why the session is classified as abandoned."""

    EXPLICIT = "EXPLICIT"  # buyer hit ABANDON_CHECKOUT
    CHECKOUT_DROPOFF = "CHECKOUT_DROPOFF"  # started checkout but didn't complete
    IDLE_TIMEOUT = "IDLE_TIMEOUT"  # had cart, never started checkout, session timed out


@dataclass(frozen=True, slots=True)
class AbandonedSession:
    """One session flagged for recovery."""

    session: Session
    reason: AbandonReason

    @property
    def session_id(self) -> str:
        return self.session.session_id


def find_abandoned(
    sessions: list[Session],
    *,
    min_cart_vnd: int = 50_000,
) -> list[AbandonedSession]:
    """Filter to sessions that left a non-empty cart without completing."""
    if min_cart_vnd < 0:
        raise ValueError("min_cart_vnd must be >= 0")
    out: list[AbandonedSession] = []
    for s in sessions:
        if s.completed_checkout:
            continue
        if s.n_add == 0:
            continue
        if s.cart_value_vnd < min_cart_vnd:
            continue
        if s.explicit_abandon:
            reason = AbandonReason.EXPLICIT
        elif s.started_checkout:
            reason = AbandonReason.CHECKOUT_DROPOFF
        else:
            reason = AbandonReason.IDLE_TIMEOUT
        out.append(AbandonedSession(session=s, reason=reason))
    return out


def abandon_rate(sessions: list[Session]) -> float:
    """Fraction of carting sessions that abandoned (`[0, 1]`).

    Only sessions with at least one ``ADD_TO_CART`` count toward the
    denominator — pure browse sessions are excluded, so the rate
    reflects "of buyers who tried to buy, how many gave up?"
    """
    carting = [s for s in sessions if s.n_add > 0]
    if not carting:
        return 0.0
    abandoned = sum(1 for s in carting if not s.completed_checkout)
    return abandoned / len(carting)


__all__ = ["AbandonReason", "AbandonedSession", "abandon_rate", "find_abandoned"]
