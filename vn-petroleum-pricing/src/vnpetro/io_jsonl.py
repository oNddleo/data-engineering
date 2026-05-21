"""JSONL codec for PriceBreakdown."""

from __future__ import annotations

import json

from vnpetro.pricing import PriceBreakdown
from vnpetro.schema import FuelType, PriceRegion


def breakdown_to_dict(b: PriceBreakdown) -> dict[str, object]:
    return {
        "fuel_type": b.fuel_type.value,
        "region": b.region.value,
        "cif_vnd_per_litre": b.cif_vnd_per_litre,
        "import_tariff_vnd": b.import_tariff_vnd,
        "import_cost_vnd": b.import_cost_vnd,
        "base_price_vnd": b.base_price_vnd,
        "sct_vnd": b.sct_vnd,
        "ept_vnd": b.ept_vnd,
        "vat_vnd": b.vat_vnd,
        "dealer_margin_vnd": b.dealer_margin_vnd,
        "regional_surcharge_vnd": b.regional_surcharge_vnd,
        "stabilisation_fund_vnd": b.stabilisation_fund_vnd,
        "retail_price_vnd_per_litre": b.retail_price_vnd_per_litre,
    }


def breakdown_from_dict(d: object) -> PriceBreakdown:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")

    def _s(k: str) -> str:
        v = d.get(k)
        if not isinstance(v, str):
            raise TypeError(f"{k} must be str")
        return v

    def _f(k: str, default: float = 0.0) -> float:
        v = d.get(k, default)
        if not isinstance(v, int | float):
            raise TypeError(f"{k} must be numeric")
        return float(v)

    return PriceBreakdown(
        fuel_type=FuelType(_s("fuel_type")),
        region=PriceRegion(_s("region")),
        cif_vnd_per_litre=_f("cif_vnd_per_litre"),
        import_tariff_vnd=_f("import_tariff_vnd"),
        import_cost_vnd=_f("import_cost_vnd"),
        base_price_vnd=_f("base_price_vnd"),
        sct_vnd=_f("sct_vnd"),
        ept_vnd=_f("ept_vnd"),
        vat_vnd=_f("vat_vnd"),
        dealer_margin_vnd=_f("dealer_margin_vnd"),
        regional_surcharge_vnd=_f("regional_surcharge_vnd"),
        stabilisation_fund_vnd=_f("stabilisation_fund_vnd"),
        retail_price_vnd_per_litre=_f("retail_price_vnd_per_litre"),
    )


def dump(breakdowns: list[PriceBreakdown]) -> str:
    lines = [json.dumps(breakdown_to_dict(b), ensure_ascii=False) for b in breakdowns]
    return "\n".join(lines) + ("\n" if lines else "")


def load(text: str) -> list[PriceBreakdown]:
    out: list[PriceBreakdown] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(breakdown_from_dict(raw))
    return out
