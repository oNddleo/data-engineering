"""Filter operator — drop records that don't satisfy a predicate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ivm.operators.base import Operator

if TYPE_CHECKING:
    from collections.abc import Callable

    from ivm.types import Record, Update


class FilterOperator(Operator):
    """Passes through updates whose record satisfies predicate(record) == True.

    The diff (insertion/retraction) is preserved unchanged.
    """

    def __init__(self, predicate: Callable[[Record], bool]) -> None:
        super().__init__()
        self.predicate = predicate

    def process(self, updates: list[Update]) -> list[Update]:
        """Keep only updates whose record passes the predicate."""
        return [u for u in updates if self.predicate(u.record)]

    def _unused(self) -> Any:  # pragma: no cover
        return None
