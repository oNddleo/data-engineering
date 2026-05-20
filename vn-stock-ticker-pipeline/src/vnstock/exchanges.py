"""VN stock exchange directory — trading rules per exchange.

Each exchange has distinct **price band**, **lot size**, and **tick
size** rules set by Bộ Tài Chính (Ministry of Finance) and SSC
(State Securities Commission). Current rules (2025):

| Exchange | Band (normal) | Band (IPO) | Lot size | Notes                  |
| -------- | ------------- | ---------- | -------- | ---------------------- |
| HOSE     | ±7%           | ±20%       | 100      | Multi-tier tick size   |
| HNX      | ±10%          | ±30%       | 100      | Flat 100 VND tick      |
| UPCOM    | ±15%          | ±40%       | 100      | Flat 100 VND tick      |

Tick size (HOSE only — HNX/UPCoM use a flat 100 VND tick):

| Price range (VND)  | Tick (VND) |
| ------------------ | ---------- |
| < 10 000           | 10         |
| 10 000 – 49 950    | 50         |
| ≥ 50 000           | 100        |
"""

from __future__ import annotations

from dataclasses import dataclass

from vnstock.schema import Exchange


@dataclass(frozen=True, slots=True)
class ExchangeProfile:
    """Trading-rule snapshot for one VN equity exchange."""

    code: Exchange
    name_vi: str
    name_en: str
    price_band_bps: int  # ±band in basis points (10_000 = 100%)
    ipo_band_bps: int  # ±band on the IPO listing day
    lot_size: int  # minimum tradable share count
    flat_tick_vnd: int  # 0 → tiered (HOSE); positive → flat


_PROFILES: tuple[ExchangeProfile, ...] = (
    ExchangeProfile(
        code=Exchange.HOSE,
        name_vi="Sở Giao Dịch Chứng Khoán TP. Hồ Chí Minh",
        name_en="Ho Chi Minh City Stock Exchange",
        price_band_bps=700,  # ±7%
        ipo_band_bps=2_000,  # ±20%
        lot_size=100,
        flat_tick_vnd=0,  # tiered
    ),
    ExchangeProfile(
        code=Exchange.HNX,
        name_vi="Sở Giao Dịch Chứng Khoán Hà Nội",
        name_en="Hanoi Stock Exchange",
        price_band_bps=1_000,  # ±10%
        ipo_band_bps=3_000,  # ±30%
        lot_size=100,
        flat_tick_vnd=100,
    ),
    ExchangeProfile(
        code=Exchange.UPCOM,
        name_vi="Thị Trường Cổ Phiếu Công Ty Đại Chúng Chưa Niêm Yết",
        name_en="Unlisted Public Company Market",
        price_band_bps=1_500,  # ±15%
        ipo_band_bps=4_000,  # ±40%
        lot_size=100,
        flat_tick_vnd=100,
    ),
)


_BY_CODE: dict[Exchange, ExchangeProfile] = {p.code: p for p in _PROFILES}


def all_exchanges() -> tuple[ExchangeProfile, ...]:
    return _PROFILES


def profile_for(exchange: Exchange) -> ExchangeProfile:
    """Return the bundled profile for ``exchange``.

    Always returns a profile — raises if the enum value is unknown
    (defensive; the three bundled members cover the union).
    """
    profile = _BY_CODE.get(exchange)
    if profile is None:  # pragma: no cover - defensive
        raise ValueError(f"unknown exchange {exchange!r}")
    return profile


__all__ = [
    "ExchangeProfile",
    "all_exchanges",
    "profile_for",
]
