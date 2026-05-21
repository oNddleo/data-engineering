"""JSONL codec for PricedLot."""

from __future__ import annotations

import json

from vncoffee.pricing import PricedLot, price_lot
from vncoffee.schema import (
    CoffeeGrade,
    CoffeeSpecies,
    ContractType,
    ExportLot,
    Incoterm,
)


def lot_to_dict(p: PricedLot) -> dict[str, object]:
    lot = p.lot
    return {
        "lot_id": lot.lot_id,
        "species": lot.species.value,
        "grade": lot.grade.value,
        "contract": lot.contract.value,
        "incoterm": lot.incoterm.value,
        "volume_mt": lot.volume_mt,
        "futures_price_usd_mt": lot.futures_price_usd_mt,
        "differential_usd_mt": lot.differential_usd_mt,
        "fixed_price_usd_mt": lot.fixed_price_usd_mt,
        "freight_usd_mt": lot.freight_usd_mt,
        "insurance_rate_pct": lot.insurance_rate_pct,
        "fob_price_usd_mt": p.fob_price_usd_mt,
        "total_fob_usd": p.total_fob_usd,
        "total_contract_usd": p.total_contract_usd,
    }


def lot_from_dict(d: object) -> PricedLot:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")

    def _s(key: str) -> str:
        v = d.get(key)
        if not isinstance(v, str):
            raise TypeError(f"{key} must be str")
        return v

    def _f(key: str, default: float = 0.0) -> float:
        v = d.get(key, default)
        if not isinstance(v, int | float):
            raise TypeError(f"{key} must be numeric")
        return float(v)

    lot = ExportLot(
        lot_id=_s("lot_id"),
        species=CoffeeSpecies(_s("species")),
        grade=CoffeeGrade(_s("grade")),
        contract=ContractType(_s("contract")),
        incoterm=Incoterm(_s("incoterm")),
        volume_mt=_f("volume_mt"),
        futures_price_usd_mt=_f("futures_price_usd_mt"),
        differential_usd_mt=_f("differential_usd_mt"),
        fixed_price_usd_mt=_f("fixed_price_usd_mt"),
        freight_usd_mt=_f("freight_usd_mt"),
        insurance_rate_pct=_f("insurance_rate_pct"),
    )
    return price_lot(lot)


def dump(lots: list[PricedLot]) -> str:
    lines = [json.dumps(lot_to_dict(p), ensure_ascii=False) for p in lots]
    return "\n".join(lines) + ("\n" if lines else "")


def load(text: str) -> list[PricedLot]:
    out: list[PricedLot] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(lot_from_dict(raw))
    return out
