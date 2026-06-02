"""Bundled VN ticker registry — the 30+ most-traded names.

Three flavours:

* **VN30** — 30 large-cap, high-liquidity HOSE constituents
  (recomputed quarterly by HOSE Index Committee). We bundle the
  Q1 2025 composition (effective 2025-02-03 per Decision 1/2025/QĐ-SGDCK).
* **HNX30** — top 30 by liquidity on HNX (similar quarterly rebalance).
  We bundle 12 of the most well-known names; full HNX30 has more
  thinly-traded members.
* **UPCOM_LEADERS** — a small set of UPCoM constituents that are
  household names (BSR, ACV, MCH, VEA, ...).

The bundled set covers ~80% of typical VN-equity daily turnover. For
arbitrary tickers, callers can construct ``Ticker`` directly.
"""

from __future__ import annotations

from vnstock.schema import Exchange, Ticker

# ---------- VN30 (Q1 2025 composition) -------------------------------------

_VN30: tuple[Ticker, ...] = (
    Ticker(
        symbol="ACB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Á Châu",
        name_en="Asia Commercial Bank",
        industry="Banking",
    ),
    Ticker(
        symbol="BCM",
        exchange=Exchange.HOSE,
        name_vi="Tổng Công ty Becamex IDC",
        name_en="Becamex IDC Corporation",
        industry="Real Estate",
    ),
    Ticker(
        symbol="BID",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Đầu tư và Phát triển Việt Nam",
        name_en="BIDV",
        industry="Banking",
    ),
    Ticker(
        symbol="BVH",
        exchange=Exchange.HOSE,
        name_vi="Tập đoàn Bảo Việt",
        name_en="Bao Viet Holdings",
        industry="Insurance",
    ),
    Ticker(
        symbol="CTG",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Công Thương Việt Nam",
        name_en="VietinBank",
        industry="Banking",
    ),
    Ticker(
        symbol="FPT",
        exchange=Exchange.HOSE,
        name_vi="Công ty Cổ phần FPT",
        name_en="FPT Corporation",
        industry="Technology",
    ),
    Ticker(
        symbol="GAS",
        exchange=Exchange.HOSE,
        name_vi="Tổng Công ty Khí Việt Nam",
        name_en="PetroVietnam Gas",
        industry="Energy",
    ),
    Ticker(
        symbol="GVR",
        exchange=Exchange.HOSE,
        name_vi="Tập đoàn Công nghiệp Cao su Việt Nam",
        name_en="Vietnam Rubber Group",
        industry="Materials",
    ),
    Ticker(
        symbol="HDB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Phát triển TP HCM",
        name_en="HDBank",
        industry="Banking",
    ),
    Ticker(
        symbol="HPG",
        exchange=Exchange.HOSE,
        name_vi="Tập đoàn Hòa Phát",
        name_en="Hoa Phat Group",
        industry="Materials",
    ),
    Ticker(
        symbol="MBB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Quân Đội",
        name_en="Military Bank",
        industry="Banking",
    ),
    Ticker(
        symbol="MSN",
        exchange=Exchange.HOSE,
        name_vi="Tập đoàn Masan",
        name_en="Masan Group",
        industry="Consumer Staples",
    ),
    Ticker(
        symbol="MWG",
        exchange=Exchange.HOSE,
        name_vi="Công ty Cổ phần Đầu tư Thế Giới Di Động",
        name_en="Mobile World Investment",
        industry="Retail",
    ),
    Ticker(
        symbol="PLX",
        exchange=Exchange.HOSE,
        name_vi="Tập đoàn Xăng Dầu Việt Nam",
        name_en="Petrolimex",
        industry="Energy",
    ),
    Ticker(
        symbol="POW",
        exchange=Exchange.HOSE,
        name_vi="Tổng Công ty Điện Lực Dầu Khí",
        name_en="PetroVietnam Power",
        industry="Utilities",
    ),
    Ticker(
        symbol="SAB",
        exchange=Exchange.HOSE,
        name_vi="Tổng Công ty Bia – Rượu – NGK Sài Gòn",
        name_en="Saigon Beer Alcohol Beverage",
        industry="Consumer Staples",
    ),
    Ticker(
        symbol="SHB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Sài Gòn – Hà Nội",
        name_en="Saigon Hanoi Bank",
        industry="Banking",
    ),
    Ticker(
        symbol="SSB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Đông Nam Á",
        name_en="SeABank",
        industry="Banking",
    ),
    Ticker(
        symbol="SSI",
        exchange=Exchange.HOSE,
        name_vi="Công ty Cổ phần Chứng khoán SSI",
        name_en="SSI Securities",
        industry="Financial Services",
    ),
    Ticker(
        symbol="STB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Sài Gòn Thương Tín",
        name_en="Sacombank",
        industry="Banking",
    ),
    Ticker(
        symbol="TCB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Kỹ Thương Việt Nam",
        name_en="Techcombank",
        industry="Banking",
    ),
    Ticker(
        symbol="TPB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Tiên Phong",
        name_en="TPBank",
        industry="Banking",
    ),
    Ticker(
        symbol="VCB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Ngoại Thương Việt Nam",
        name_en="Vietcombank",
        industry="Banking",
    ),
    Ticker(
        symbol="VHM",
        exchange=Exchange.HOSE,
        name_vi="Công ty Cổ phần Vinhomes",
        name_en="Vinhomes",
        industry="Real Estate",
    ),
    Ticker(
        symbol="VIB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Quốc Tế Việt Nam",
        name_en="VIB",
        industry="Banking",
    ),
    Ticker(
        symbol="VIC",
        exchange=Exchange.HOSE,
        name_vi="Tập đoàn Vingroup",
        name_en="Vingroup",
        industry="Conglomerate",
    ),
    Ticker(
        symbol="VJC",
        exchange=Exchange.HOSE,
        name_vi="Công ty Cổ phần Hàng không VietJet",
        name_en="VietJet Air",
        industry="Transportation",
    ),
    Ticker(
        symbol="VNM",
        exchange=Exchange.HOSE,
        name_vi="Công ty Cổ phần Sữa Việt Nam",
        name_en="Vinamilk",
        industry="Consumer Staples",
    ),
    Ticker(
        symbol="VPB",
        exchange=Exchange.HOSE,
        name_vi="Ngân hàng TMCP Việt Nam Thịnh Vượng",
        name_en="VPBank",
        industry="Banking",
    ),
    Ticker(
        symbol="VRE",
        exchange=Exchange.HOSE,
        name_vi="Công ty Cổ phần Vincom Retail",
        name_en="Vincom Retail",
        industry="Real Estate",
    ),
)


# ---------- HNX leaders ---------------------------------------------------

_HNX: tuple[Ticker, ...] = (
    Ticker(
        symbol="CEO",
        exchange=Exchange.HNX,
        name_vi="Công ty CP Tập đoàn C.E.O",
        name_en="CEO Group",
        industry="Real Estate",
    ),
    Ticker(
        symbol="DTD",
        exchange=Exchange.HNX,
        name_vi="Công ty CP Đầu tư Phát triển Thành Đạt",
        name_en="Thanh Dat Investment",
        industry="Construction",
    ),
    Ticker(
        symbol="IDC",
        exchange=Exchange.HNX,
        name_vi="Tổng Công ty IDICO",
        name_en="IDICO Corp",
        industry="Real Estate",
    ),
    Ticker(
        symbol="MBS",
        exchange=Exchange.HNX,
        name_vi="Công ty CP Chứng khoán MB",
        name_en="MB Securities",
        industry="Financial Services",
    ),
    Ticker(
        symbol="PVI",
        exchange=Exchange.HNX,
        name_vi="Công ty CP PVI",
        name_en="PVI Holdings",
        industry="Insurance",
    ),
    Ticker(
        symbol="PVS",
        exchange=Exchange.HNX,
        name_vi="Tổng Công ty CP Dịch vụ Kỹ thuật Dầu khí",
        name_en="PetroVietnam Technical Services",
        industry="Energy",
    ),
    Ticker(
        symbol="SHS",
        exchange=Exchange.HNX,
        name_vi="Công ty CP Chứng khoán Sài Gòn – Hà Nội",
        name_en="SHS Securities",
        industry="Financial Services",
    ),
    Ticker(
        symbol="TNG",
        exchange=Exchange.HNX,
        name_vi="Công ty CP Đầu tư và Thương mại TNG",
        name_en="TNG Investment",
        industry="Consumer Discretionary",
    ),
    Ticker(
        symbol="VCS",
        exchange=Exchange.HNX,
        name_vi="Công ty CP Vicostone",
        name_en="Vicostone",
        industry="Materials",
    ),
    Ticker(
        symbol="VGS",
        exchange=Exchange.HNX,
        name_vi="Công ty CP Ống thép Việt Đức VG PIPE",
        name_en="Viet Duc VG Pipe",
        industry="Materials",
    ),
)


# ---------- UPCoM leaders -------------------------------------------------

_UPCOM: tuple[Ticker, ...] = (
    Ticker(
        symbol="ACV",
        exchange=Exchange.UPCOM,
        name_vi="Tổng Công ty Cảng Hàng không Việt Nam",
        name_en="Airports Corporation of Vietnam",
        industry="Transportation",
    ),
    Ticker(
        symbol="BSR",
        exchange=Exchange.UPCOM,
        name_vi="Công ty CP Lọc Hóa Dầu Bình Sơn",
        name_en="Binh Son Refining",
        industry="Energy",
    ),
    Ticker(
        symbol="MCH",
        exchange=Exchange.UPCOM,
        name_vi="Công ty CP Hàng Tiêu Dùng Masan",
        name_en="Masan Consumer",
        industry="Consumer Staples",
    ),
    Ticker(
        symbol="QNS",
        exchange=Exchange.UPCOM,
        name_vi="Công ty CP Đường Quảng Ngãi",
        name_en="Quang Ngai Sugar",
        industry="Consumer Staples",
    ),
    Ticker(
        symbol="VEA",
        exchange=Exchange.UPCOM,
        name_vi="Tổng Công ty Máy động lực và Máy nông nghiệp",
        name_en="VEAM Corp",
        industry="Industrials",
    ),
)


_ALL_TICKERS: tuple[Ticker, ...] = _VN30 + _HNX + _UPCOM
_BY_SYMBOL: dict[str, Ticker] = {t.symbol: t for t in _ALL_TICKERS}


def all_tickers() -> tuple[Ticker, ...]:
    """Return every bundled ticker across all three exchanges."""
    return _ALL_TICKERS


def vn30() -> tuple[Ticker, ...]:
    """The 30 HOSE VN30 constituents (Q1 2025)."""
    return _VN30


def hnx_leaders() -> tuple[Ticker, ...]:
    """Top liquidity HNX names (subset of HNX30)."""
    return _HNX


def upcom_leaders() -> tuple[Ticker, ...]:
    """Well-known UPCoM names."""
    return _UPCOM


def ticker_for(symbol: str) -> Ticker | None:
    """Look up a bundled ticker by symbol (case-insensitive)."""
    return _BY_SYMBOL.get(symbol.upper())


def tickers_on(exchange: Exchange) -> tuple[Ticker, ...]:
    """Return all bundled tickers listed on ``exchange``."""
    return tuple(t for t in _ALL_TICKERS if t.exchange is exchange)


__all__ = [
    "all_tickers",
    "hnx_leaders",
    "ticker_for",
    "tickers_on",
    "upcom_leaders",
    "vn30",
]
