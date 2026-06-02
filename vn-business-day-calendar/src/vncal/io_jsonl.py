"""JSONL codec for Holiday + FiscalYear."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from vncal.schema import FiscalYear, Holiday, HolidayKind

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d[key]
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def holiday_to_dict(h: Holiday) -> dict[str, object]:
    return {
        "date": h.date.isoformat(),
        "name_vi": h.name_vi,
        "name_en": h.name_en,
        "kind": h.kind.value,
        "paid": h.paid,
    }


def holiday_from_dict(d: dict[str, object]) -> Holiday:
    return Holiday(
        date=date.fromisoformat(_require_str(d, "date")),
        name_vi=_require_str(d, "name_vi"),
        name_en=_require_str(d, "name_en"),
        kind=HolidayKind(_require_str(d, "kind")),
        paid=_require_bool(d, "paid") if "paid" in d else True,
    )


def fiscal_year_to_dict(fy: FiscalYear) -> dict[str, object]:
    return {
        "label": fy.label,
        "start_date": fy.start_date.isoformat(),
        "end_date": fy.end_date.isoformat(),
    }


def fiscal_year_from_dict(d: dict[str, object]) -> FiscalYear:
    return FiscalYear(
        label=_require_str(d, "label"),
        start_date=date.fromisoformat(_require_str(d, "start_date")),
        end_date=date.fromisoformat(_require_str(d, "end_date")),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_holidays(items: Iterable[Holiday]) -> str:
    return _dump(holiday_to_dict(h) for h in items)


def dump_fiscal_years(items: Iterable[FiscalYear]) -> str:
    return _dump(fiscal_year_to_dict(fy) for fy in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_holidays(text: str) -> list[Holiday]:
    return [holiday_from_dict(d) for d in _iter_lines(text)]


def load_fiscal_years(text: str) -> list[FiscalYear]:
    return [fiscal_year_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_fiscal_years",
    "dump_holidays",
    "fiscal_year_from_dict",
    "fiscal_year_to_dict",
    "holiday_from_dict",
    "holiday_to_dict",
    "load_fiscal_years",
    "load_holidays",
]
