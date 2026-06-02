"""VN ride-hailing operator directory + city directory.

**Operators (2026 active commission-based platforms).** Each has a
distinct commission split per service type, expressed in basis
points (10_000 bps = 100%). Real-world rates published by the
operators (or reverse-engineered from driver-forum reports):

* **Grab** — ~25% car, ~20% bike. Market leader (~70% share).
* **Be** — VN-owned, ~20% car, ~15% bike. ~25% share.
* **Xanh SM** — VinFast EV taxi. Two operating models exist; we model
  the cooperative-driver flavour at ~15% / ~12%. (The flagship
  salaried-fleet drivers don't appear in commission settlements.)
* **Maxim** — Russian-origin operator, low-cost, ~15% / ~10%.

Gojek Vietnam shut down on 2024-09-16; we do not bundle it.

**Cities.** Six VN tier-1 and tier-2 cities. Surge pricing follows
operator policy plus city-level "high-demand windows" (Tết Eve,
typhoon-rain peak hour, big concerts) — we expose a simple
``base_surge_during_peak`` to colour the simulator.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OperatorProfile:
    """One commission-based ride-hailing platform."""

    abbreviation: str
    name_vi: str
    name_en: str
    commission_car_bps: int
    commission_bike_bps: int
    commission_delivery_bps: int
    market_share_pct: float

    def __post_init__(self) -> None:
        if not self.abbreviation:
            raise ValueError("abbreviation must be non-empty")
        for name, val in (
            ("commission_car_bps", self.commission_car_bps),
            ("commission_bike_bps", self.commission_bike_bps),
            ("commission_delivery_bps", self.commission_delivery_bps),
        ):
            if not 0 <= val <= 10_000:
                raise ValueError(f"{name} must be in [0, 10_000], got {val}")


@dataclass(frozen=True, slots=True)
class CityProfile:
    """One serviced VN city."""

    code: str  # 3-letter, e.g. SGN
    name_vi: str
    name_en: str
    population_thousands: int
    base_surge_during_peak_bps: int  # default surge during rush/rain


_OPERATORS: tuple[OperatorProfile, ...] = (
    OperatorProfile(
        abbreviation="GRAB",
        name_vi="Grab Việt Nam",
        name_en="Grab Vietnam",
        commission_car_bps=2_500,  # 25%
        commission_bike_bps=2_000,  # 20%
        commission_delivery_bps=2_500,
        market_share_pct=68.0,
    ),
    OperatorProfile(
        abbreviation="BE",
        name_vi="Công ty CP Be Group",
        name_en="Be Group",
        commission_car_bps=2_000,
        commission_bike_bps=1_500,
        commission_delivery_bps=2_000,
        market_share_pct=24.0,
    ),
    OperatorProfile(
        abbreviation="XANHSM",
        name_vi="Xanh SM (Công ty GSM)",
        name_en="Xanh SM (Green and Smart Mobility)",
        commission_car_bps=1_500,
        commission_bike_bps=1_200,
        commission_delivery_bps=1_500,
        market_share_pct=6.0,
    ),
    OperatorProfile(
        abbreviation="MAXIM",
        name_vi="Maxim Việt Nam",
        name_en="Maxim Vietnam",
        commission_car_bps=1_500,
        commission_bike_bps=1_000,
        commission_delivery_bps=1_500,
        market_share_pct=2.0,
    ),
)


_CITIES: tuple[CityProfile, ...] = (
    CityProfile(
        code="SGN",
        name_vi="Thành phố Hồ Chí Minh",
        name_en="Ho Chi Minh City",
        population_thousands=9_000,
        base_surge_during_peak_bps=14_000,
    ),
    CityProfile(
        code="HAN",
        name_vi="Hà Nội",
        name_en="Hanoi",
        population_thousands=8_500,
        base_surge_during_peak_bps=13_500,
    ),
    CityProfile(
        code="DAD",
        name_vi="Đà Nẵng",
        name_en="Da Nang",
        population_thousands=1_300,
        base_surge_during_peak_bps=12_000,
    ),
    CityProfile(
        code="HPH",
        name_vi="Hải Phòng",
        name_en="Hai Phong",
        population_thousands=2_100,
        base_surge_during_peak_bps=12_000,
    ),
    CityProfile(
        code="CTH",
        name_vi="Cần Thơ",
        name_en="Can Tho",
        population_thousands=1_250,
        base_surge_during_peak_bps=11_500,
    ),
    CityProfile(
        code="NHA",
        name_vi="Nha Trang",
        name_en="Nha Trang",
        population_thousands=550,
        base_surge_during_peak_bps=11_500,
    ),
)


_OP_BY_ABBR: dict[str, OperatorProfile] = {o.abbreviation: o for o in _OPERATORS}
_CITY_BY_CODE: dict[str, CityProfile] = {c.code: c for c in _CITIES}


def all_operators() -> tuple[OperatorProfile, ...]:
    return _OPERATORS


def all_cities() -> tuple[CityProfile, ...]:
    return _CITIES


def operator_for(abbr: str) -> OperatorProfile | None:
    """Look up an operator by abbreviation (case-insensitive)."""
    return _OP_BY_ABBR.get(abbr.upper())


def city_for(code: str) -> CityProfile | None:
    """Look up a city by 3-letter code (case-insensitive)."""
    return _CITY_BY_CODE.get(code.upper())


def commission_bps(operator: str, service: str) -> int:
    """Look up the commission basis-points for a given (operator, service)."""
    op = operator_for(operator)
    if op is None:
        raise ValueError(f"unknown operator {operator!r}")
    s = service.upper()
    if s == "CAR":
        return op.commission_car_bps
    if s == "BIKE":
        return op.commission_bike_bps
    if s == "DELIVERY":
        return op.commission_delivery_bps
    raise ValueError(f"unknown service {service!r}")


__all__ = [
    "CityProfile",
    "OperatorProfile",
    "all_cities",
    "all_operators",
    "city_for",
    "commission_bps",
    "operator_for",
]
