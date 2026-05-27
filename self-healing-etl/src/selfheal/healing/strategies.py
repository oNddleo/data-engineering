"""HealingEngine: backfill, coerce, and evolve strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selfheal.schema.drift import DriftEvent
    from selfheal.schema.registry import SchemaRegistry

# ---------------------------------------------------------------------------
# Type coercion helpers
# ---------------------------------------------------------------------------

_COERCE_MAP: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
}


def _coerce_value(value: object, target_type_name: str) -> object:
    """Attempt to coerce *value* to *target_type_name*.

    Raises :class:`ValueError` if coercion is not possible.
    """
    target_type = _COERCE_MAP.get(target_type_name)
    if target_type is None:
        raise ValueError(f"Unknown target type: {target_type_name!r}")
    try:
        return target_type(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Cannot coerce {value!r} to {target_type_name!r}: {exc}") from exc


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class HealResult:
    """Outcome of a single record-level healing attempt."""

    healed: bool
    record: dict[str, object]
    strategy_used: str | None = None
    failure_reason: str | None = None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class HealingEngine:
    """Apply healing strategies to records that exhibit schema drift.

    Parameters
    ----------
    registry:
        The :class:`~selfheal.schema.registry.SchemaRegistry` used to look up
        the authoritative schema for *source_name*.
    source_name:
        The data source whose schema should be consulted.
    """

    def __init__(self, registry: SchemaRegistry, source_name: str) -> None:
        self._registry = registry
        self._source_name = source_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def heal(
        self,
        record: dict[str, object],
        drift_events: list[DriftEvent],
    ) -> HealResult:
        """Attempt to heal *record* by addressing each drift event.

        Returns a :class:`HealResult` describing success or failure.
        """
        from selfheal.schema.drift import DriftType  # noqa: PLC0415

        working = dict(record)
        strategies_used: list[str] = []

        for event in drift_events:
            if event.drift_type == DriftType.COLUMN_REMOVED:
                result = self._backfill(working, event)
            elif event.drift_type == DriftType.TYPE_CHANGED:
                result = self._coerce(working, event)
            elif event.drift_type == DriftType.COLUMN_ADDED:
                result = self._evolve(working, event)
            else:  # pragma: no cover
                return HealResult(
                    healed=False,
                    record=record,
                    failure_reason=f"Unknown drift type: {event.drift_type}",
                )

            if not result.healed:
                return HealResult(
                    healed=False,
                    record=record,
                    failure_reason=result.failure_reason,
                )
            working = result.record
            if result.strategy_used:
                strategies_used.append(result.strategy_used)

        return HealResult(
            healed=True,
            record=working,
            strategy_used=", ".join(strategies_used) if strategies_used else None,
        )

    # ------------------------------------------------------------------
    # Individual strategies
    # ------------------------------------------------------------------

    def _backfill(
        self,
        record: dict[str, object],
        event: DriftEvent,
    ) -> HealResult:
        """Strategy: COLUMN_REMOVED — insert a default value for the missing column."""
        target_type_name = event.old_type or "str"
        default = self._default_for(target_type_name)
        record = dict(record)
        record[event.column] = default
        return HealResult(healed=True, record=record, strategy_used="backfill")

    def _coerce(
        self,
        record: dict[str, object],
        event: DriftEvent,
    ) -> HealResult:
        """Strategy: TYPE_CHANGED — coerce the column value to the registered type."""
        target_type_name = event.old_type  # registered type is the authority
        if target_type_name is None:
            return HealResult(
                healed=False,
                record=record,
                failure_reason="TYPE_CHANGED event has no old_type",
            )
        record = dict(record)
        value = record.get(event.column)
        try:
            record[event.column] = _coerce_value(value, target_type_name)
        except ValueError as exc:
            return HealResult(healed=False, record=record, failure_reason=str(exc))
        return HealResult(healed=True, record=record, strategy_used="coerce")

    def _evolve(
        self,
        record: dict[str, object],
        event: DriftEvent,
    ) -> HealResult:
        """Strategy: COLUMN_ADDED — accept the new column and register the schema update."""
        entry = self._registry.get_active(self._source_name)
        if entry is not None:
            new_schema = dict(entry.schema)
            new_schema[event.column] = event.new_type or "str"
            self._registry.register(self._source_name, new_schema)
        return HealResult(healed=True, record=dict(record), strategy_used="evolve")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_for(type_name: str) -> object:
        """Return a sensible zero/default value for a given type name."""
        defaults: dict[str, object] = {
            "int": 0,
            "float": 0.0,
            "str": "",
            "bool": False,
        }
        return defaults.get(type_name, None)
