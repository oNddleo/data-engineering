"""JSONL codec for ExportRecord."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from vnfishery.schema import ExportRecord, Form, Grade, Market, Species

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def record_to_dict(r: ExportRecord) -> dict[str, object]:
    return {
        "shipment_id": r.shipment_id,
        "exporter_tax_code": r.exporter_tax_code,
        "species": r.species.value,
        "market": r.market.value,
        "grade": r.grade.value,
        "form": r.form.value,
        "weight_kg": r.weight_kg,
        "fob_price_usd_cents_per_kg": r.fob_price_usd_cents_per_kg,
        "shipped_on": r.shipped_on.isoformat(),
    }


def record_from_dict(d: dict[str, object]) -> ExportRecord:
    return ExportRecord(
        shipment_id=_require_str(d, "shipment_id"),
        exporter_tax_code=_require_str(d, "exporter_tax_code"),
        species=Species(_require_str(d, "species")),
        market=Market(_require_str(d, "market")),
        grade=Grade(_require_str(d, "grade")),
        form=Form(_require_str(d, "form")),
        weight_kg=_require_int(d, "weight_kg"),
        fob_price_usd_cents_per_kg=_require_int(d, "fob_price_usd_cents_per_kg"),
        shipped_on=date.fromisoformat(_require_str(d, "shipped_on")),
    )


def dump_records(items: Iterable[ExportRecord]) -> str:
    return "\n".join(json.dumps(record_to_dict(r), ensure_ascii=False) for r in items) + "\n"


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(
                f"expected JSON object per line, got {type(parsed).__name__}",
            )
        yield parsed


def load_records(text: str) -> list[ExportRecord]:
    return [record_from_dict(d) for d in _iter_lines(text)]


__all__ = ["dump_records", "load_records", "record_from_dict", "record_to_dict"]
