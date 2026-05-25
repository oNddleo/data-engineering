"""Incremental aggregate functions.

Each Aggregate exposes:
  initial_state()  -> opaque state value
  add(state, value, diff) -> new state   (diff is +1 or -1)
  result(state)    -> the aggregate value to emit
  is_empty(state)  -> True when the group has zero rows (should be omitted)

All aggregates correctly handle retractions (diff = -1) because they track
full multiplicity, not just presence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from typing import Any


class Aggregate(ABC):
    """Abstract base class for incremental aggregates."""

    @abstractmethod
    def initial_state(self) -> Any:
        """Return the initial (empty) aggregate state."""
        ...

    @abstractmethod
    def add(self, state: Any, value: Any, diff: int) -> Any:
        """Apply one update (with multiplicity diff) to the aggregate state."""
        ...

    @abstractmethod
    def result(self, state: Any) -> Any:
        """Compute the aggregate result from the current state."""
        ...

    def is_empty(self, state: Any) -> bool:
        """Return True when the group has zero rows."""
        return False


# ---------------------------------------------------------------------------
# COUNT(*)
# ---------------------------------------------------------------------------


class Count(Aggregate):
    """COUNT(*) — counts rows with multiplicity support."""

    def initial_state(self) -> int:
        return 0

    def add(self, state: int, value: Any, diff: int) -> int:
        return state + diff

    def result(self, state: int) -> int:
        return max(0, state)

    def is_empty(self, state: int) -> bool:
        return state <= 0


# ---------------------------------------------------------------------------
# SUM(column)
# ---------------------------------------------------------------------------


class Sum(Aggregate):
    """SUM(column) — sum of a numeric column with retraction support."""

    def __init__(self, column: str) -> None:
        self.column = column

    def initial_state(self) -> dict[str, Any]:
        return {"sum": 0, "count": 0}

    def add(self, state: dict[str, Any], value: Any, diff: int) -> dict[str, Any]:
        return {"sum": state["sum"] + diff * value, "count": state["count"] + diff}

    def result(self, state: dict[str, Any]) -> float | None:
        return state["sum"] if state["count"] > 0 else None

    def is_empty(self, state: dict[str, Any]) -> bool:
        return state["count"] <= 0  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# AVG(column)
# ---------------------------------------------------------------------------


class Avg(Aggregate):
    """AVG(column) — running average with retraction support."""

    def __init__(self, column: str) -> None:
        self.column = column

    def initial_state(self) -> dict[str, Any]:
        return {"sum": 0.0, "count": 0}

    def add(self, state: dict[str, Any], value: Any, diff: int) -> dict[str, Any]:
        return {"sum": state["sum"] + diff * value, "count": state["count"] + diff}

    def result(self, state: dict[str, Any]) -> float | None:
        return state["sum"] / state["count"] if state["count"] > 0 else None

    def is_empty(self, state: dict[str, Any]) -> bool:
        return state["count"] <= 0  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# MIN / MAX — use a counter so retractions work correctly
# ---------------------------------------------------------------------------


class Min(Aggregate):
    """MIN with retraction support: tracks value → multiplicity."""

    def __init__(self, column: str) -> None:
        self.column = column

    def initial_state(self) -> Counter[Any]:
        return Counter()

    def add(self, state: Counter[Any], value: Any, diff: int) -> Counter[Any]:
        nxt: Counter[Any] = Counter(state)
        nxt[value] += diff
        if nxt[value] <= 0:
            del nxt[value]
        return nxt

    def result(self, state: Counter[Any]) -> Any:
        return min(state.keys()) if state else None

    def is_empty(self, state: Counter[Any]) -> bool:
        return not state


class Max(Aggregate):
    """MAX with retraction support: tracks value → multiplicity."""

    def __init__(self, column: str) -> None:
        self.column = column

    def initial_state(self) -> Counter[Any]:
        return Counter()

    def add(self, state: Counter[Any], value: Any, diff: int) -> Counter[Any]:
        nxt: Counter[Any] = Counter(state)
        nxt[value] += diff
        if nxt[value] <= 0:
            del nxt[value]
        return nxt

    def result(self, state: Counter[Any]) -> Any:
        return max(state.keys()) if state else None

    def is_empty(self, state: Counter[Any]) -> bool:
        return not state


# ---------------------------------------------------------------------------
# COUNT(DISTINCT column)
# ---------------------------------------------------------------------------


class CountDistinct(Aggregate):
    """COUNT(DISTINCT column) — counts unique values with retraction support."""

    def __init__(self, column: str) -> None:
        self.column = column

    def initial_state(self) -> Counter[Any]:
        return Counter()

    def add(self, state: Counter[Any], value: Any, diff: int) -> Counter[Any]:
        nxt: Counter[Any] = Counter(state)
        nxt[value] += diff
        if nxt[value] <= 0:
            del nxt[value]
        return nxt

    def result(self, state: Counter[Any]) -> int:
        return len(state)

    def is_empty(self, state: Counter[Any]) -> bool:
        return not state


# ---------------------------------------------------------------------------
# Convenience aliases
# ---------------------------------------------------------------------------

count = Count
count_distinct = CountDistinct


def sum_(column: str) -> Sum:
    """Factory for Sum(column)."""
    return Sum(column)


def avg(column: str) -> Avg:
    """Factory for Avg(column)."""
    return Avg(column)


def min_(column: str) -> Min:
    """Factory for Min(column)."""
    return Min(column)


def max_(column: str) -> Max:
    """Factory for Max(column)."""
    return Max(column)
