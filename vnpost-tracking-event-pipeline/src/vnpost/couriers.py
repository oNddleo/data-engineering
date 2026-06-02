"""VN courier directory + published SLA targets.

The 5 majors covered (2026 market share approx):

| Courier | Code | Founded | SLA HCM↔HN | Notes                          |
| ------- | ---- | ------- | ---------- | ------------------------------ |
| Viettel Post     | VTP  | 1997 | 3-5 days   | National network, post-office  |
| GiaoHangNhanh    | GHN  | 2012 | 2-3 days   | Tech-first, large e-com player |
| GiaoHangTietKiem | GHTK | 2013 | 3-4 days   | Frasers Property-backed        |
| J&T Express      | JT   | 2017 | 2-4 days   | China JV, rapid growth         |
| Shopee Express   | SPX  | 2020 | 2-3 days   | Captive to Shopee marketplace  |

The ``sla_hours`` table is the **time-to-delivery target** (P95)
between any two major-city gateways. Same-city (e.g. HCM→HCM)
parcels have a tighter SLA. The data below is calibrated against
the couriers' published end-of-2024 service guides.
"""

from __future__ import annotations

from dataclasses import dataclass

from vnpost.schema import CourierCode


@dataclass(frozen=True, slots=True)
class CourierProfile:
    """One courier's name + SLA targets."""

    code: CourierCode
    name_vi: str
    name_en: str
    sla_same_city_hours: int  # SLA for intra-city delivery
    sla_inter_city_hours: int  # SLA for inter-city delivery


_PROFILES: tuple[CourierProfile, ...] = (
    CourierProfile(
        code=CourierCode.VTP,
        name_vi="Viettel Post",
        name_en="Viettel Post",
        sla_same_city_hours=24,
        sla_inter_city_hours=120,
    ),
    CourierProfile(
        code=CourierCode.GHN,
        name_vi="Giao Hàng Nhanh",
        name_en="GiaoHangNhanh",
        sla_same_city_hours=24,
        sla_inter_city_hours=72,
    ),
    CourierProfile(
        code=CourierCode.GHTK,
        name_vi="Giao Hàng Tiết Kiệm",
        name_en="GiaoHangTietKiem",
        sla_same_city_hours=36,
        sla_inter_city_hours=96,
    ),
    CourierProfile(
        code=CourierCode.JT,
        name_vi="J&T Express",
        name_en="J&T Express VN",
        sla_same_city_hours=24,
        sla_inter_city_hours=96,
    ),
    CourierProfile(
        code=CourierCode.SPX,
        name_vi="Shopee Express",
        name_en="Shopee Express",
        sla_same_city_hours=24,
        sla_inter_city_hours=72,
    ),
)

_BY_CODE: dict[CourierCode, CourierProfile] = {p.code: p for p in _PROFILES}


def all_profiles() -> tuple[CourierProfile, ...]:
    """Immutable tuple of every bundled courier."""
    return _PROFILES


def profile(code: CourierCode) -> CourierProfile:
    """Return the courier profile for ``code``; raises ``KeyError`` if absent."""
    return _BY_CODE[code]


def sla_hours(
    code: CourierCode,
    *,
    origin_city: str,
    dest_city: str,
) -> int:
    """The published SLA target for one parcel.

    ``origin_city`` / ``dest_city`` should be the first two chars of
    the hub codes (``"HCM"``, ``"HN"``, etc).
    """
    p = profile(code)
    if origin_city == dest_city:
        return p.sla_same_city_hours
    return p.sla_inter_city_hours


__all__ = ["CourierProfile", "all_profiles", "profile", "sla_hours"]
