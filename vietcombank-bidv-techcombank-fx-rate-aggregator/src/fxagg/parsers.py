"""Bank-specific FX-rate parsers.

Every Vietnamese bank publishes the same conceptual data — buy/sell
rates for ~10 currencies — but in wildly different on-the-wire
formats. We support four canonical shapes that cover most of the
top-10:

* **Vietcombank XML** (``parse_vietcombank_xml``) — the public feed
  at ``vietcombank.com.vn/api/exchangerates`` is an
  ``<ExrateList>`` document with one ``<Exrate>`` element per
  currency carrying ``CurrencyCode``, ``Buy``, ``Transfer``, ``Sell``
  attributes plus a top-level ``<DateTime>``.
* **BIDV HTML** (``parse_bidv_html``) — a single ``<table>`` with
  rows ``<tr><td>USD</td><td>24,800</td><td>24,830</td><td>25,180</td></tr>``.
  The timestamp lives in a header element above the table.
* **Techcombank JSON** (``parse_techcombank_json``) — typical
  REST-API response, ``{"data": {"datetime": ..., "rates": [...]}}``.
* **Generic CSV** (``parse_generic_csv``) — for any bank willing to
  publish a CSV: header row ``currency,buy_cash,buy_transfer,sell``
  plus a separate ``quoted_at`` argument.

Every parser returns a :class:`Snapshot`. Malformed input raises
:class:`ParseError` with the bank kind, row number, and field name
so the data-engineering on-call can find the offending byte
immediately.
"""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser

from fxagg.schema import VN_TZ, Bank, Currency, Quote, Snapshot


class ParseError(Exception):
    """Raised when a vendor payload can't be turned into a Snapshot."""

    def __init__(self, vendor: str, field: str, message: str) -> None:
        super().__init__(f"{vendor}: {field}: {message}")
        self.vendor = vendor
        self.field = field
        self.message = message


_NUMBER_RE = re.compile(r"[\d.,]+")


def _parse_int_amount(raw: str) -> int:
    """Tolerate ``"24,800"`` / ``"24.800"`` / ``"24 800"`` formats."""
    digits = raw.replace(",", "").replace(".", "").replace(" ", "").strip()
    if not digits:
        raise ValueError(f"empty amount {raw!r}")
    if not digits.lstrip("-").isdigit():
        raise ValueError(f"not a number: {raw!r}")
    return int(digits)


# ---------------------------------------------------------------------------
# Vietcombank XML


def parse_vietcombank_xml(xml_text: str) -> Snapshot:
    """Parse the Vietcombank ``<ExrateList>`` feed."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ParseError("vietcombank", "root", f"malformed XML: {e}") from e

    dt_el = root.find("DateTime")
    if dt_el is None or not (dt_el.text or "").strip():
        raise ParseError("vietcombank", "DateTime", "missing <DateTime> element")
    quoted_at = _parse_vcb_datetime(dt_el.text or "")

    quotes: list[Quote] = []
    for rate_el in root.findall("Exrate"):
        code = (rate_el.get("CurrencyCode") or "").strip()
        if not code:
            raise ParseError("vietcombank", "CurrencyCode", "missing attribute")
        try:
            currency = Currency(code)
        except ValueError:
            # Unknown currency code → skip silently; the bank may publish
            # currencies we don't care about (e.g. SAR, RUB).
            continue
        buy_cash_raw = rate_el.get("Buy") or ""
        transfer_raw = rate_el.get("Transfer") or ""
        sell_raw = rate_el.get("Sell") or ""
        try:
            buy_cash = _parse_int_amount(buy_cash_raw) if buy_cash_raw.strip() else None
            buy_transfer = _parse_int_amount(transfer_raw)
            sell = _parse_int_amount(sell_raw)
        except ValueError as e:
            raise ParseError("vietcombank", code, str(e)) from e
        quotes.append(
            Quote(
                bank=Bank.VCB,
                currency=currency,
                buy_transfer_vnd=buy_transfer,
                sell_vnd=sell,
                quoted_at=quoted_at,
                buy_cash_vnd=buy_cash,
            )
        )
    return Snapshot(bank=Bank.VCB, quoted_at=quoted_at, quotes=tuple(quotes))


def _parse_vcb_datetime(raw: str) -> datetime:
    """Vietcombank stamps ``yyyy-MM-dd HH:mm:ss`` in local (UTC+7) time."""
    raw = raw.strip()
    try:
        naive = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        raise ParseError("vietcombank", "DateTime", f"not yyyy-MM-dd HH:mm:ss: {raw!r}") from e
    return naive.replace(tzinfo=VN_TZ)


# ---------------------------------------------------------------------------
# BIDV HTML


class _BIDVHTMLExtractor(HTMLParser):
    """Pull out one ``<table>`` of currency rows from a BIDV-style page."""

    def __init__(self) -> None:
        super().__init__()
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._row: list[str] = []
        self._cell_text: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._row = []
        elif self._in_row and tag in ("td", "th"):
            self._in_cell = True
            self._cell_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self._in_table = False
        elif self._in_table and tag == "tr":
            if self._row:
                self.rows.append(self._row)
            self._in_row = False
        elif self._in_row and tag in ("td", "th"):
            self._row.append("".join(self._cell_text).strip())
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_text.append(data)


_BIDV_TIMESTAMP_RE = re.compile(
    r"(?:cập nhật|updated|as of)[^0-9]*"
    r"(\d{1,2}[:/h]\d{2}(?:[:.]\d{2})?\s*(?:\d{1,2}/\d{1,2}/\d{4})?)",
    re.IGNORECASE,
)


def parse_bidv_html(html_text: str, *, quoted_at: datetime) -> Snapshot:
    """Parse a BIDV-style HTML page.

    The page has zero structured timestamp — the data engineer must
    pass ``quoted_at`` explicitly (typically: when the scraper ran).
    """
    extractor = _BIDVHTMLExtractor()
    extractor.feed(html_text)
    quotes: list[Quote] = []
    for row in extractor.rows:
        if len(row) < 4:
            continue
        code, buy_cash_raw, transfer_raw, sell_raw = row[0], row[1], row[2], row[3]
        if not code or not code.isalpha():
            continue
        try:
            currency = Currency(code)
        except ValueError:
            continue
        try:
            buy_cash = _parse_int_amount(buy_cash_raw) if buy_cash_raw.strip() else None
            buy_transfer = _parse_int_amount(transfer_raw)
            sell = _parse_int_amount(sell_raw)
        except ValueError as e:
            raise ParseError("bidv", code, str(e)) from e
        quotes.append(
            Quote(
                bank=Bank.BIDV,
                currency=currency,
                buy_transfer_vnd=buy_transfer,
                sell_vnd=sell,
                quoted_at=quoted_at,
                buy_cash_vnd=buy_cash,
            )
        )
    return Snapshot(bank=Bank.BIDV, quoted_at=quoted_at, quotes=tuple(quotes))


# ---------------------------------------------------------------------------
# Techcombank JSON


def parse_techcombank_json(json_text: str) -> Snapshot:
    """Parse Techcombank's REST API response shape."""
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ParseError("techcombank", "root", f"malformed JSON: {e}") from e
    if not isinstance(payload, dict):
        raise ParseError("techcombank", "root", "expected object at root")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ParseError("techcombank", "data", "expected object")
    dt_raw = data.get("datetime")
    if not isinstance(dt_raw, str):
        raise ParseError("techcombank", "datetime", "missing or non-string")
    try:
        quoted_at = datetime.fromisoformat(dt_raw)
    except ValueError as e:
        raise ParseError("techcombank", "datetime", f"not ISO-8601: {e}") from e
    if quoted_at.tzinfo is None:
        quoted_at = quoted_at.replace(tzinfo=VN_TZ)
    rates = data.get("rates")
    if not isinstance(rates, list):
        raise ParseError("techcombank", "rates", "expected array")
    quotes: list[Quote] = []
    for entry in rates:
        if not isinstance(entry, dict):
            continue
        code_obj = entry.get("currency")
        if not isinstance(code_obj, str):
            continue
        try:
            currency = Currency(code_obj)
        except ValueError:
            continue
        buy_cash_obj = entry.get("buyCash")
        buy_transfer_obj = entry.get("buyTransfer")
        sell_obj = entry.get("sell")
        if not (isinstance(buy_transfer_obj, int) and isinstance(sell_obj, int)):
            raise ParseError("techcombank", code_obj, "buyTransfer/sell must be int")
        buy_cash = buy_cash_obj if isinstance(buy_cash_obj, int) else None
        quotes.append(
            Quote(
                bank=Bank.TCB,
                currency=currency,
                buy_transfer_vnd=buy_transfer_obj,
                sell_vnd=sell_obj,
                quoted_at=quoted_at,
                buy_cash_vnd=buy_cash,
            )
        )
    return Snapshot(bank=Bank.TCB, quoted_at=quoted_at, quotes=tuple(quotes))


# ---------------------------------------------------------------------------
# Generic CSV


def parse_generic_csv(csv_text: str, *, bank: Bank, quoted_at: datetime) -> Snapshot:
    """Parse a CSV: ``currency,buy_cash,buy_transfer,sell``."""
    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"currency", "buy_cash", "buy_transfer", "sell"}
    rows = list(reader)
    if not rows:
        return Snapshot(bank=bank, quoted_at=quoted_at, quotes=())
    missing = required - set(rows[0].keys())
    if missing:
        raise ParseError(f"{bank.value}-csv", "header", f"missing columns: {sorted(missing)}")
    quotes: list[Quote] = []
    for i, row in enumerate(rows, start=2):
        code = (row["currency"] or "").strip()
        try:
            currency = Currency(code)
        except ValueError:
            continue
        try:
            buy_cash = _parse_int_amount(row["buy_cash"]) if row["buy_cash"].strip() else None
            buy_transfer = _parse_int_amount(row["buy_transfer"])
            sell = _parse_int_amount(row["sell"])
        except ValueError as e:
            raise ParseError(f"{bank.value}-csv", f"row {i}", str(e)) from e
        quotes.append(
            Quote(
                bank=bank,
                currency=currency,
                buy_transfer_vnd=buy_transfer,
                sell_vnd=sell,
                quoted_at=quoted_at,
                buy_cash_vnd=buy_cash,
            )
        )
    return Snapshot(bank=bank, quoted_at=quoted_at, quotes=tuple(quotes))


__all__ = [
    "ParseError",
    "parse_bidv_html",
    "parse_generic_csv",
    "parse_techcombank_json",
    "parse_vietcombank_xml",
]
