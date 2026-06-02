"""Trip state machine: transition validation + terminal classification."""

from __future__ import annotations

import pytest

from vnride.schema import TripState
from vnride.state_machine import (
    allowed_next,
    is_terminal,
    validate_history,
    validate_transition,
)

# ---------- is_terminal -----------------------------------------------------


@pytest.mark.parametrize(
    "state",
    [
        TripState.COMPLETED,
        TripState.CANCELLED,
        TripState.NO_DRIVER,
    ],
)
def test_terminal_states(state: TripState) -> None:
    assert is_terminal(state) is True


@pytest.mark.parametrize(
    "state",
    [
        TripState.REQUESTED,
        TripState.ASSIGNED,
        TripState.ARRIVING,
        TripState.PICKED_UP,
    ],
)
def test_non_terminal_states(state: TripState) -> None:
    assert is_terminal(state) is False


# ---------- allowed_next ----------------------------------------------------


def test_allowed_next_requested() -> None:
    out = allowed_next(TripState.REQUESTED)
    assert out == frozenset(
        {
            TripState.ASSIGNED,
            TripState.CANCELLED,
            TripState.NO_DRIVER,
        }
    )


def test_allowed_next_completed_empty() -> None:
    """Terminal states allow no transitions."""
    assert allowed_next(TripState.COMPLETED) == frozenset()
    assert allowed_next(TripState.CANCELLED) == frozenset()
    assert allowed_next(TripState.NO_DRIVER) == frozenset()


# ---------- validate_transition ---------------------------------------------


def test_validate_legal_transition_happy_path() -> None:
    # All happy-path edges.
    validate_transition(TripState.REQUESTED, TripState.ASSIGNED)
    validate_transition(TripState.ASSIGNED, TripState.ARRIVING)
    validate_transition(TripState.ARRIVING, TripState.PICKED_UP)
    validate_transition(TripState.PICKED_UP, TripState.COMPLETED)


def test_validate_legal_no_driver_path() -> None:
    validate_transition(TripState.REQUESTED, TripState.NO_DRIVER)


def test_validate_legal_cancel_paths() -> None:
    for src in (
        TripState.REQUESTED,
        TripState.ASSIGNED,
        TripState.ARRIVING,
        TripState.PICKED_UP,
    ):
        validate_transition(src, TripState.CANCELLED)


def test_validate_rejects_skipping_states() -> None:
    """Can't jump REQUESTED → PICKED_UP."""
    with pytest.raises(ValueError, match="illegal"):
        validate_transition(TripState.REQUESTED, TripState.PICKED_UP)


def test_validate_rejects_completed_transition() -> None:
    """Nothing can come after COMPLETED."""
    with pytest.raises(ValueError, match="illegal"):
        validate_transition(TripState.COMPLETED, TripState.CANCELLED)


def test_validate_rejects_backwards() -> None:
    """Trip cannot go backwards."""
    with pytest.raises(ValueError, match="illegal"):
        validate_transition(TripState.ARRIVING, TripState.REQUESTED)


def test_validate_no_driver_terminal() -> None:
    """NO_DRIVER is terminal."""
    with pytest.raises(ValueError, match="illegal"):
        validate_transition(TripState.NO_DRIVER, TripState.ASSIGNED)


# ---------- validate_history -----------------------------------------------


def test_validate_history_happy_path() -> None:
    validate_history(
        [
            TripState.REQUESTED,
            TripState.ASSIGNED,
            TripState.ARRIVING,
            TripState.PICKED_UP,
            TripState.COMPLETED,
        ]
    )


def test_validate_history_must_start_at_requested() -> None:
    with pytest.raises(ValueError, match="REQUESTED"):
        validate_history([TripState.ASSIGNED, TripState.ARRIVING])


def test_validate_history_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_history([])


def test_validate_history_catches_illegal_hop() -> None:
    with pytest.raises(ValueError, match="illegal"):
        validate_history(
            [
                TripState.REQUESTED,
                TripState.ASSIGNED,
                TripState.COMPLETED,
            ]
        )
