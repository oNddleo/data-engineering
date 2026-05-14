"""Shared test fixtures + factories."""

from __future__ import annotations

from datetime import datetime, timedelta

from fxagg.schema import VN_TZ, Bank, Currency, Quote


def make_quote(
    *,
    bank: Bank = Bank.VCB,
    currency: Currency = Currency.USD,
    buy_transfer: int = 25_000,
    sell: int = 25_200,
    quoted_at: datetime | None = None,
    buy_cash: int | None = 24_950,
) -> Quote:
    return Quote(
        bank=bank,
        currency=currency,
        buy_transfer_vnd=buy_transfer,
        sell_vnd=sell,
        quoted_at=quoted_at or datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ),
        buy_cash_vnd=buy_cash,
    )


def t_at(minutes: int) -> datetime:
    return datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ) + timedelta(minutes=minutes)


VCB_XML = """<ExrateList>
<DateTime>2026-05-14 09:30:00</DateTime>
<Exrate CurrencyCode="USD" CurrencyName="US DOLLAR" Buy="24800" Transfer="24830" Sell="25180"/>
<Exrate CurrencyCode="EUR" CurrencyName="EURO" Buy="26500" Transfer="26800" Sell="27500"/>
<Exrate CurrencyCode="JPY" CurrencyName="JAPANESE YEN" Buy="165" Transfer="167" Sell="174"/>
<Exrate CurrencyCode="XYZ" CurrencyName="UNKNOWN" Buy="1" Transfer="1" Sell="1"/>
<Source>Vietcombank</Source>
</ExrateList>
"""

BIDV_HTML = """<html>
<body>
<h2>Tỷ giá ngoại tệ - cập nhật lúc 09:30 14/05/2026</h2>
<table>
<tr><th>Mã NT</th><th>Mua TM</th><th>Mua CK</th><th>Bán</th></tr>
<tr><td>USD</td><td>24,800</td><td>24,830</td><td>25,180</td></tr>
<tr><td>EUR</td><td>26,500</td><td>26,800</td><td>27,500</td></tr>
<tr><td>JPY</td><td>165</td><td>167</td><td>174</td></tr>
<tr><td>NOTACUR</td><td>1</td><td>1</td><td>1</td></tr>
</table>
</body>
</html>
"""

TCB_JSON = """{
  "status": "OK",
  "data": {
    "datetime": "2026-05-14T09:30:00+07:00",
    "rates": [
      {"currency": "USD", "buyCash": 24800, "buyTransfer": 24830, "sell": 25180},
      {"currency": "EUR", "buyCash": 26500, "buyTransfer": 26800, "sell": 27500},
      {"currency": "JPY", "buyCash": 165,   "buyTransfer": 167,   "sell": 174}
    ]
  }
}
"""

GENERIC_CSV = """currency,buy_cash,buy_transfer,sell
USD,24800,24830,25180
EUR,26500,26800,27500
JPY,165,167,174
"""

__all__ = ["BIDV_HTML", "GENERIC_CSV", "TCB_JSON", "VCB_XML", "make_quote", "t_at"]
