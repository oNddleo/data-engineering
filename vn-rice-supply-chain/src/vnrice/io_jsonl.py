"""JSONL codec for ExportQuote."""

from __future__ import annotations

import json

from vnrice.milling import mill
from vnrice.pricing import ExportQuote, quote_export
from vnrice.schema import MilledRiceSpec, PaddyGrade, PaddyLot, RiceVariety


def quote_to_dict(q: ExportQuote) -> dict[str, object]:
    p = q.milled.paddy
    return {
        "lot_id": p.lot_id,
        "variety": p.variety.value,
        "grade": p.grade.value,
        "weight_mt": p.weight_mt,
        "moisture_pct": p.moisture_pct,
        "price_vnd_per_kg": p.price_vnd_per_kg,
        "broken_spec": q.milled.broken_spec.value,
        "dry_weight_mt": q.milled.dry_weight_mt,
        "white_rice_mt": q.milled.white_rice_mt,
        "milling_yield_pct": q.milled.milling_yield_pct,
        "fob_price_usd_mt": q.fob_price_usd_mt,
        "total_fob_usd": q.total_fob_usd,
        "gross_margin_usd": q.gross_margin_usd,
    }


def quote_from_dict(d: object) -> ExportQuote:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")

    def _s(k: str) -> str:
        v = d.get(k)
        if not isinstance(v, str):
            raise TypeError(f"{k} must be str")
        return v

    def _f(k: str) -> float:
        v = d.get(k)
        if not isinstance(v, int | float):
            raise TypeError(f"{k} must be numeric")
        return float(v)

    lot = PaddyLot(
        lot_id=_s("lot_id"),
        variety=RiceVariety(_s("variety")),
        grade=PaddyGrade(_s("grade")),
        weight_mt=_f("weight_mt"),
        moisture_pct=_f("moisture_pct"),
        price_vnd_per_kg=_f("price_vnd_per_kg"),
    )
    spec = MilledRiceSpec(_s("broken_spec"))
    milled = mill(lot, spec)
    return quote_export(milled)


def dump(quotes: list[ExportQuote]) -> str:
    lines = [json.dumps(quote_to_dict(q), ensure_ascii=False) for q in quotes]
    return "\n".join(lines) + ("\n" if lines else "")


def load(text: str) -> list[ExportQuote]:
    out: list[ExportQuote] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(quote_from_dict(raw))
    return out
