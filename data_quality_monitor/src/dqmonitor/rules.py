"""Rule base class and concrete rule implementations for dqmonitor."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class Rule(ABC):
    """Abstract base class for all data quality rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this rule."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the rule."""

    @abstractmethod
    def check(self, record: dict[str, object]) -> bool:
        """Return True if the record passes this rule, False otherwise."""

    def reset(self) -> None:  # noqa: B027
        """Reset any per-batch state. Called before each Validator.validate() call."""


# ---------------------------------------------------------------------------
# Concrete rules
# ---------------------------------------------------------------------------


class NotNullRule(Rule):
    """Fails if the specified column is None or missing from the record."""

    def __init__(self, column: str) -> None:
        self._column = column

    @property
    def name(self) -> str:
        return f"not_null({self._column})"

    @property
    def description(self) -> str:
        return f"Column '{self._column}' must not be null or missing."

    @property
    def column(self) -> str:
        return self._column

    def check(self, record: dict[str, object]) -> bool:
        return record.get(self._column) is not None and self._column in record


class UniqueRule(Rule):
    """Stateful rule — fails on duplicate values within a batch."""

    def __init__(self, column: str) -> None:
        self._column = column
        self._seen: set[object] = set()

    @property
    def name(self) -> str:
        return f"unique({self._column})"

    @property
    def description(self) -> str:
        return f"Column '{self._column}' must be unique within each batch."

    @property
    def column(self) -> str:
        return self._column

    def check(self, record: dict[str, object]) -> bool:
        value = record.get(self._column)
        if value in self._seen:
            return False
        self._seen.add(value)
        return True

    def reset(self) -> None:
        self._seen = set()


class RangeCheckRule(Rule):
    """Fails if the numeric value is outside [min_val, max_val]."""

    def __init__(self, column: str, min_val: float, max_val: float) -> None:
        self._column = column
        self._min = min_val
        self._max = max_val

    @property
    def name(self) -> str:
        return f"range({self._column},{self._min},{self._max})"

    @property
    def description(self) -> str:
        return f"Column '{self._column}' must be a number in " f"[{self._min}, {self._max}]."

    @property
    def column(self) -> str:
        return self._column

    @property
    def min_val(self) -> float:
        return self._min

    @property
    def max_val(self) -> float:
        return self._max

    def check(self, record: dict[str, object]) -> bool:
        value = record.get(self._column)
        if value is None:
            return False
        try:
            numeric = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
        return self._min <= numeric <= self._max


class RegexMatchRule(Rule):
    """Fails if the string representation of the value does not match *pattern*."""

    def __init__(self, column: str, pattern: str) -> None:
        self._column = column
        self._pattern = pattern
        self._compiled = re.compile(pattern)

    @property
    def name(self) -> str:
        return f"regex({self._column},{self._pattern})"

    @property
    def description(self) -> str:
        return f"Column '{self._column}' must match pattern '{self._pattern}'."

    @property
    def column(self) -> str:
        return self._column

    @property
    def pattern(self) -> str:
        return self._pattern

    def check(self, record: dict[str, object]) -> bool:
        value = record.get(self._column)
        if value is None:
            return False
        return self._compiled.match(str(value)) is not None


class ReferentialIntegrityRule(Rule):
    """Fails if the column value is not in the allowed set."""

    def __init__(self, column: str, allowed_values: set[object]) -> None:
        self._column = column
        self._allowed = frozenset(allowed_values)

    @property
    def name(self) -> str:
        return f"referential_integrity({self._column})"

    @property
    def description(self) -> str:
        return f"Column '{self._column}' must be one of the allowed values."

    @property
    def column(self) -> str:
        return self._column

    @property
    def allowed_values(self) -> frozenset[object]:
        return self._allowed

    def check(self, record: dict[str, object]) -> bool:
        return record.get(self._column) in self._allowed


class CustomPredicateRule(Rule):
    """Applies a caller-supplied predicate function to each record."""

    def __init__(
        self,
        rule_name: str,
        predicate: Callable[[dict[str, object]], bool],
        rule_description: str = "",
    ) -> None:
        self._name = rule_name
        self._predicate = predicate
        self._description = rule_description or f"Custom predicate '{rule_name}'."

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def check(self, record: dict[str, object]) -> bool:
        return self._predicate(record)
