"""Project operator — reshape records by selecting or transforming columns."""
from __future__ import annotations

from typing import Any, Callable

from ivm.operators.base import Operator
from ivm.types import Record, Update


class ProjectOperator(Operator):
    """Emit a transformed version of each record.

    Provide either:
      columns   — list of column names to keep
      transform — callable(record) -> new_record

    If both are provided, columns is applied first, then transform.
    """

    def __init__(
        self,
        columns: list[str] | None = None,
        transform: Callable[[Record], Record] | None = None,
    ) -> None:
        super().__init__()
        self.columns = columns
        self.transform = transform

    def _apply(self, record: Record) -> Record:
        result: Record = dict(record)
        if self.columns is not None:
            result = {k: record[k] for k in self.columns if k in record}
        if self.transform is not None:
            result = self.transform(result)
        return result

    def process(self, updates: list[Update]) -> list[Update]:
        """Apply the projection/transform to every record in the batch."""
        return [Update(self._apply(u.record), u.timestamp, u.diff) for u in updates]

    # Needed for mypy strict: unused type param Any suppressed inline
    def _unused(self) -> Any:  # pragma: no cover
        return None
