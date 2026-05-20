"""Trip state machine — allowed transitions + validation.

The lifecycle of a trip:

.. code::

                  +-------> NO_DRIVER     (system failed to match)
                  |
    REQUESTED --> ASSIGNED --> ARRIVING --> PICKED_UP --> COMPLETED
        |             |             |             |
        +-------------+-------------+-------------+-----> CANCELLED

Cancellations can happen from any non-terminal state. Once a trip
reaches ``COMPLETED``, ``CANCELLED``, or ``NO_DRIVER`` it is terminal
and cannot transition further.

``validate_transition(old, new)`` returns silently on a legal hop and
raises ``ValueError`` otherwise.
"""

from __future__ import annotations

from vnride.schema import TripState

_TERMINAL = {TripState.COMPLETED, TripState.CANCELLED, TripState.NO_DRIVER}

_ALLOWED: dict[TripState, frozenset[TripState]] = {
    TripState.REQUESTED: frozenset(
        {
            TripState.ASSIGNED,
            TripState.CANCELLED,
            TripState.NO_DRIVER,
        }
    ),
    TripState.ASSIGNED: frozenset(
        {
            TripState.ARRIVING,
            TripState.CANCELLED,
        }
    ),
    TripState.ARRIVING: frozenset(
        {
            TripState.PICKED_UP,
            TripState.CANCELLED,
        }
    ),
    TripState.PICKED_UP: frozenset(
        {
            TripState.COMPLETED,
            TripState.CANCELLED,
        }
    ),
    TripState.COMPLETED: frozenset(),
    TripState.CANCELLED: frozenset(),
    TripState.NO_DRIVER: frozenset(),
}


def is_terminal(state: TripState) -> bool:
    """``True`` if no further transition is allowed."""
    return state in _TERMINAL


def allowed_next(state: TripState) -> frozenset[TripState]:
    """Return the set of legal next states from ``state``."""
    return _ALLOWED[state]


def validate_transition(old: TripState, new: TripState) -> None:
    """Raise ``ValueError`` if ``old → new`` is not a legal transition."""
    if new not in _ALLOWED[old]:
        raise ValueError(
            f"illegal trip transition: {old.value} → {new.value}",
        )


def validate_history(states: list[TripState]) -> None:
    """Validate a complete state sequence (e.g. an event log replay)."""
    if not states:
        raise ValueError("state history must not be empty")
    if states[0] is not TripState.REQUESTED:
        raise ValueError(
            f"state history must start with REQUESTED, got {states[0].value}",
        )
    for i in range(1, len(states)):
        validate_transition(states[i - 1], states[i])


__all__ = [
    "allowed_next",
    "is_terminal",
    "validate_history",
    "validate_transition",
]
