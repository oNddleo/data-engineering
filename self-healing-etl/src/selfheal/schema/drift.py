"""DriftDetector: compare batch schema vs registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DriftType(Enum):
    """Categories of schema drift."""

    COLUMN_ADDED = "COLUMN_ADDED"
    COLUMN_REMOVED = "COLUMN_REMOVED"
    TYPE_CHANGED = "TYPE_CHANGED"


@dataclass
class DriftEvent:
    """Describes a single schema drift incident."""

    column: str
    drift_type: DriftType
    old_type: str | None  # None for COLUMN_ADDED
    new_type: str | None  # None for COLUMN_REMOVED
    severity: str  # "low" | "medium" | "high"

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict (JSON-safe)."""
        return {
            "column": self.column,
            "drift_type": self.drift_type.value,
            "old_type": self.old_type,
            "new_type": self.new_type,
            "severity": self.severity,
        }


def _severity_for(drift_type: DriftType) -> str:
    """Return a default severity string for a given drift type."""
    if drift_type == DriftType.COLUMN_REMOVED:
        return "high"
    if drift_type == DriftType.TYPE_CHANGED:
        return "medium"
    return "low"  # COLUMN_ADDED


class DriftDetector:
    """Compare an incoming batch schema against a registered schema.

    Parameters
    ----------
    registered_schema:
        The currently-active ``{column: type}`` mapping from
        :class:`~selfheal.schema.registry.SchemaRegistry`.
    """

    def __init__(self, registered_schema: dict[str, str]) -> None:
        self._registered = dict(registered_schema)

    # ------------------------------------------------------------------

    def detect(self, batch_schema: dict[str, str]) -> list[DriftEvent]:
        """Return a list of :class:`DriftEvent` objects describing every drift.

        Parameters
        ----------
        batch_schema:
            The ``{column: type}`` mapping inferred from the incoming batch.
        """
        events: list[DriftEvent] = []
        registered = self._registered
        batch = dict(batch_schema)

        # Columns that exist in the registry but are absent from the batch.
        for col in registered:
            if col not in batch:
                events.append(
                    DriftEvent(
                        column=col,
                        drift_type=DriftType.COLUMN_REMOVED,
                        old_type=registered[col],
                        new_type=None,
                        severity=_severity_for(DriftType.COLUMN_REMOVED),
                    )
                )

        # Columns in the batch that are absent from the registry, or whose
        # type has changed.
        for col, new_type in batch.items():
            if col not in registered:
                events.append(
                    DriftEvent(
                        column=col,
                        drift_type=DriftType.COLUMN_ADDED,
                        old_type=None,
                        new_type=new_type,
                        severity=_severity_for(DriftType.COLUMN_ADDED),
                    )
                )
            elif registered[col] != new_type:
                events.append(
                    DriftEvent(
                        column=col,
                        drift_type=DriftType.TYPE_CHANGED,
                        old_type=registered[col],
                        new_type=new_type,
                        severity=_severity_for(DriftType.TYPE_CHANGED),
                    )
                )

        return events

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @staticmethod
    def infer_schema(records: list[dict[str, object]]) -> dict[str, str]:
        """Infer a ``{column: type_name}`` schema from a list of records.

        Uses the *first* non-``None`` value found per column.  Falls back
        to ``"str"`` when all values are ``None`` or the list is empty.
        """
        schema: dict[str, str] = {}
        for record in records:
            for key, value in record.items():
                if key not in schema and value is not None:
                    schema[key] = type(value).__name__
        # Ensure every key that appeared at all is present.
        for record in records:
            for key in record:
                if key not in schema:
                    schema[key] = "str"
        return schema
