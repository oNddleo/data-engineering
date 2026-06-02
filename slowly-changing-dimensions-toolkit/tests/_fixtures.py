"""Canonical builders for tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from scdkit.schema import VN_TZ, ChangeKind, DimensionChange, DimensionRow

DEFAULT_TS = datetime(2026, 5, 17, 9, 0, 0, tzinfo=VN_TZ)


def make_row(**overrides: Any) -> DimensionRow:
    defaults = {
        "natural_key": "S-001",
        "attributes": {"shop_name": "Shop Saigon", "tier": "STANDARD"},
    }
    defaults.update(overrides)
    return DimensionRow(**defaults)  # type: ignore[arg-type]


def make_change(**overrides: Any) -> DimensionChange:
    defaults: dict[str, Any] = {
        "natural_key": "S-001",
        "kind": ChangeKind.INSERT,
        "detected_at": DEFAULT_TS,
        "before": None,
        "after": {"shop_name": "Shop Saigon", "tier": "STANDARD"},
        "changed_attrs": (),
    }
    defaults.update(overrides)
    return DimensionChange(**defaults)


def make_update_change(
    natural_key: str = "S-001",
    before: dict[str, str] | None = None,
    after: dict[str, str] | None = None,
    changed_attrs: tuple[str, ...] | None = None,
    detected_at: datetime | None = None,
) -> DimensionChange:
    bef = before if before is not None else {"shop_name": "Old", "tier": "STANDARD"}
    aft = after if after is not None else {"shop_name": "New", "tier": "STANDARD"}
    ca = changed_attrs if changed_attrs is not None else ("shop_name",)
    ts = detected_at or DEFAULT_TS
    return DimensionChange(
        natural_key=natural_key,
        kind=ChangeKind.UPDATE,
        detected_at=ts,
        before=bef,
        after=aft,
        changed_attrs=ca,
    )


def make_delete_change(
    natural_key: str = "S-001",
    before: dict[str, str] | None = None,
    detected_at: datetime | None = None,
) -> DimensionChange:
    bef = before if before is not None else {"shop_name": "Shop", "tier": "STANDARD"}
    ts = detected_at or DEFAULT_TS
    return DimensionChange(
        natural_key=natural_key,
        kind=ChangeKind.DELETE,
        detected_at=ts,
        before=bef,
        after=None,
        changed_attrs=(),
    )


__all__ = [
    "DEFAULT_TS",
    "make_change",
    "make_delete_change",
    "make_row",
    "make_update_change",
]
