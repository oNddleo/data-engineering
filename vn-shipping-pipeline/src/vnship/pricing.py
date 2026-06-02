"""Fee calculation for VN domestic carriers.

All fees in VND.  Weight tiers use billable weight = max(actual, volumetric/5000).
For simplicity this module works with actual weight only; volumetric conversion
is the caller's responsibility.

Tier table (each row: up-to-gram inclusive → base fee):
  ≤500 g  → base A
  ≤1000 g → base B
  >1000 g → base B + per-500g step for every 500g above 1000g
"""

from __future__ import annotations

import math

from vnship.schema import Carrier, ServiceType, ShipmentRequest, ShipmentResult, ZoneType

# ---------------------------------------------------------------------------
# Rate tables
# ---------------------------------------------------------------------------

# (carrier, zone, service) → (base_fee_<=500g, base_fee_<=1000g, per_500g_above)
_BASE: dict[tuple[Carrier, ZoneType, ServiceType], tuple[int, int, int]] = {
    # GHN
    (Carrier.GHN, ZoneType.INNER_CITY, ServiceType.STANDARD): (22_000, 25_000, 2_500),
    (Carrier.GHN, ZoneType.INNER_CITY, ServiceType.EXPRESS): (28_000, 32_000, 3_000),
    (Carrier.GHN, ZoneType.INNER_CITY, ServiceType.SAME_DAY): (35_000, 40_000, 4_000),
    (Carrier.GHN, ZoneType.INTER_PROVINCE, ServiceType.STANDARD): (30_000, 35_000, 3_500),
    (Carrier.GHN, ZoneType.INTER_PROVINCE, ServiceType.EXPRESS): (40_000, 45_000, 4_500),
    # GHTK
    (Carrier.GHTK, ZoneType.INNER_CITY, ServiceType.STANDARD): (20_000, 23_000, 2_000),
    (Carrier.GHTK, ZoneType.INNER_CITY, ServiceType.EXPRESS): (26_000, 30_000, 2_800),
    (Carrier.GHTK, ZoneType.INNER_CITY, ServiceType.SAME_DAY): (33_000, 38_000, 3_800),
    (Carrier.GHTK, ZoneType.INTER_PROVINCE, ServiceType.STANDARD): (28_000, 33_000, 3_200),
    (Carrier.GHTK, ZoneType.INTER_PROVINCE, ServiceType.EXPRESS): (38_000, 43_000, 4_200),
    # J&T
    (Carrier.JT, ZoneType.INNER_CITY, ServiceType.STANDARD): (21_000, 24_000, 2_200),
    (Carrier.JT, ZoneType.INNER_CITY, ServiceType.EXPRESS): (27_000, 31_000, 2_900),
    (Carrier.JT, ZoneType.INNER_CITY, ServiceType.SAME_DAY): (34_000, 39_000, 3_900),
    (Carrier.JT, ZoneType.INTER_PROVINCE, ServiceType.STANDARD): (29_000, 34_000, 3_300),
    (Carrier.JT, ZoneType.INTER_PROVINCE, ServiceType.EXPRESS): (39_000, 44_000, 4_300),
    # Viettel Post
    (Carrier.VIETTEL, ZoneType.INNER_CITY, ServiceType.STANDARD): (19_000, 22_000, 1_900),
    (Carrier.VIETTEL, ZoneType.INNER_CITY, ServiceType.EXPRESS): (25_000, 29_000, 2_700),
    (Carrier.VIETTEL, ZoneType.INTER_PROVINCE, ServiceType.STANDARD): (27_000, 31_000, 3_000),
    (Carrier.VIETTEL, ZoneType.INTER_PROVINCE, ServiceType.EXPRESS): (36_000, 41_000, 4_000),
    # Vietnam Post
    (Carrier.VNPOST, ZoneType.INNER_CITY, ServiceType.STANDARD): (18_000, 21_000, 1_800),
    (Carrier.VNPOST, ZoneType.INNER_CITY, ServiceType.EXPRESS): (24_000, 28_000, 2_600),
    (Carrier.VNPOST, ZoneType.INTER_PROVINCE, ServiceType.STANDARD): (25_000, 30_000, 2_800),
    (Carrier.VNPOST, ZoneType.INTER_PROVINCE, ServiceType.EXPRESS): (35_000, 40_000, 3_800),
}

# COD fee: flat + pct of COD amount (in basis points, i.e. /10000)
_COD_FLAT = 3_000  # VND
_COD_RATE_BPS = 100  # 1%

# Fragile surcharge: flat per shipment
_FRAGILE_SURCHARGE = 5_000  # VND


def _weight_surcharge(weight_g: int, per_500g: int) -> int:
    """Extra fee for weight above 1 000 g in 500 g steps (rounded up)."""
    if weight_g <= 1_000:
        return 0
    extra_g = weight_g - 1_000
    steps = math.ceil(extra_g / 500)
    return steps * per_500g


def calculate_fee(req: ShipmentRequest) -> ShipmentResult:
    """Price a shipment end-to-end."""
    key = (req.carrier, req.zone, req.service)
    if key not in _BASE:
        raise ValueError(
            f"No rate for carrier={req.carrier} zone={req.zone} service={req.service}"
        )
    base_500, base_1000, per_500g = _BASE[key]

    # Base fee depends on first-kg tier
    base_fee = base_500 if req.weight_g <= 500 else base_1000

    # Weight surcharge for >1 kg
    wsurcharge = _weight_surcharge(req.weight_g, per_500g)

    # COD fee
    cod_fee = 0
    if req.cod_amount_vnd > 0:
        cod_fee = _COD_FLAT + (req.cod_amount_vnd * _COD_RATE_BPS) // 10_000

    # Fragile surcharge
    fragile = _FRAGILE_SURCHARGE if req.is_fragile else 0

    total = base_fee + wsurcharge + cod_fee + fragile
    return ShipmentResult(
        request=req,
        base_fee_vnd=base_fee,
        weight_surcharge_vnd=wsurcharge,
        cod_fee_vnd=cod_fee,
        fragile_surcharge_vnd=fragile,
        total_fee_vnd=total,
    )
