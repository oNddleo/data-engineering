"""Slowly-changing-dimension schema — the five Kimball types.

When a dimension attribute changes (a Shopee seller renames their
shop, a customer's CCCD address updates, a product changes category),
the data warehouse has five strategies to record the change.

| Type | Name              | Trade-off                                                |
| ---- | ----------------- | -------------------------------------------------------- |
| 1    | Overwrite         | no history; cheap; reports always show current state     |
| 2    | New row           | full history; effective_from / effective_to dates; ``is_current`` flag |
| 3    | Previous column   | one prior value per tracked attribute; partial history   |
| 4    | History table     | current row in main table + every change in a side table |
| 6    | Hybrid (1+2+3)    | current attr (T1) + history rows (T2) + prev value (T3)  |

A real DW often uses *different* types for different attributes on
the same dimension. ``DimensionRow`` carries arbitrary attributes
in a string-to-string dict — production callers serialise their
typed payload to strings before handing it to the toolkit.

All timestamps are timezone-aware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class SCDType(str, Enum):
    """Five Kimball types implemented in this toolkit."""

    TYPE_1 = "TYPE_1"
    TYPE_2 = "TYPE_2"
    TYPE_3 = "TYPE_3"
    TYPE_4 = "TYPE_4"
    TYPE_6 = "TYPE_6"


class ChangeKind(str, Enum):
    """Why this change event was emitted."""

    INSERT = "INSERT"  # brand-new natural key
    UPDATE = "UPDATE"  # existing key, one or more tracked attrs changed
    DELETE = "DELETE"  # natural key disappeared from new snapshot


# Sentinel "high date" used for the open-ended ``effective_to`` on the
# current Type-2 row. Common DW convention; far enough out that no
# real change-date will ever exceed it.
HIGH_DATE = datetime(9999, 12, 31, 23, 59, 59, tzinfo=VN_TZ)


@dataclass(frozen=True, slots=True)
class DimensionRow:
    """One row of a dimension table.

    ``natural_key`` identifies the entity in the source system
    (seller_id, customer_id, product_id). ``attributes`` is a plain
    string-to-string mapping — the toolkit doesn't care about typing
    beyond equality comparison.

    For SCD Type-2 outputs the row also carries ``surrogate_key``
    (a synthetic int unique per version), ``effective_from``,
    ``effective_to``, and ``is_current``. For Type-1 outputs only
    the first two fields are populated.
    """

    natural_key: str
    attributes: dict[str, str] = field(default_factory=dict)
    surrogate_key: int | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_current: bool = True
    previous_attributes: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.natural_key:
            raise ValueError("natural_key must be non-empty")
        if self.effective_from is not None and self.effective_from.tzinfo is None:
            raise ValueError("effective_from must be timezone-aware")
        if self.effective_to is not None and self.effective_to.tzinfo is None:
            raise ValueError("effective_to must be timezone-aware")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_from > self.effective_to
        ):
            raise ValueError(
                f"effective_from {self.effective_from} must be <= effective_to {self.effective_to}"
            )


@dataclass(frozen=True, slots=True)
class DimensionChange:
    """One change event — output of the ``detect`` step.

    ``before`` is ``None`` for ``INSERT`` (no prior row); ``after`` is
    ``None`` for ``DELETE`` (no new row). ``changed_attrs`` lists the
    attribute names that actually differ — empty for INSERT/DELETE.
    """

    natural_key: str
    kind: ChangeKind
    detected_at: datetime
    before: dict[str, str] | None
    after: dict[str, str] | None
    changed_attrs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.natural_key:
            raise ValueError("natural_key must be non-empty")
        if self.detected_at.tzinfo is None:
            raise ValueError("detected_at must be timezone-aware")
        if self.kind is ChangeKind.INSERT and self.before is not None:
            raise ValueError("INSERT must have before=None")
        if self.kind is ChangeKind.DELETE and self.after is not None:
            raise ValueError("DELETE must have after=None")
        if self.kind is ChangeKind.UPDATE:
            if self.before is None or self.after is None:
                raise ValueError("UPDATE must have both before and after")
            if not self.changed_attrs:
                raise ValueError("UPDATE must list at least one changed attribute")


__all__ = [
    "HIGH_DATE",
    "VN_TZ",
    "ChangeKind",
    "DimensionChange",
    "DimensionRow",
    "SCDType",
]
