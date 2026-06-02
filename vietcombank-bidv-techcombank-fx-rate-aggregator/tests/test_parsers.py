"""Tests for the four bundled vendor parsers."""

from __future__ import annotations

from datetime import datetime

import pytest

from fxagg.parsers import (
    ParseError,
    parse_bidv_html,
    parse_generic_csv,
    parse_techcombank_json,
    parse_vietcombank_xml,
)
from fxagg.schema import VN_TZ, Bank, Currency

from ._fixtures import BIDV_HTML, GENERIC_CSV, TCB_JSON, VCB_XML

# -------------------------------------------------- Vietcombank XML


def test_vcb_xml_parses_three_known_currencies():
    snap = parse_vietcombank_xml(VCB_XML)
    assert snap.bank is Bank.VCB
    codes = {q.currency for q in snap.quotes}
    assert codes == {Currency.USD, Currency.EUR, Currency.JPY}


def test_vcb_xml_skips_unknown_currency_code():
    snap = parse_vietcombank_xml(VCB_XML)
    # XYZ is in the fixture but not in our Currency enum — must be silently dropped.
    assert all(q.currency.value != "XYZ" for q in snap.quotes)


def test_vcb_xml_uses_vn_tz():
    snap = parse_vietcombank_xml(VCB_XML)
    assert snap.quoted_at == datetime(2026, 5, 14, 9, 30, tzinfo=VN_TZ)


def test_vcb_xml_amount_parsing():
    snap = parse_vietcombank_xml(VCB_XML)
    usd = snap.get(Currency.USD)
    assert usd is not None
    assert usd.buy_cash_vnd == 24_800
    assert usd.buy_transfer_vnd == 24_830
    assert usd.sell_vnd == 25_180


def test_vcb_xml_malformed_xml_raises():
    with pytest.raises(ParseError) as e:
        parse_vietcombank_xml("<ExrateList><DateTime>oops")
    assert e.value.field == "root"


def test_vcb_xml_missing_datetime_raises():
    bad = '<ExrateList><Exrate CurrencyCode="USD" Buy="1" Transfer="1" Sell="1"/></ExrateList>'
    with pytest.raises(ParseError) as e:
        parse_vietcombank_xml(bad)
    assert e.value.field == "DateTime"


def test_vcb_xml_bad_amount_raises():
    bad = """<ExrateList>
    <DateTime>2026-05-14 09:30:00</DateTime>
    <Exrate CurrencyCode="USD" Buy="not-a-number" Transfer="1" Sell="2"/>
    </ExrateList>"""
    with pytest.raises(ParseError) as e:
        parse_vietcombank_xml(bad)
    assert e.value.field == "USD"


def test_vcb_xml_bad_datetime_format():
    bad = "<ExrateList><DateTime>05/14/2026 09:30</DateTime></ExrateList>"
    with pytest.raises(ParseError) as e:
        parse_vietcombank_xml(bad)
    assert e.value.field == "DateTime"


# -------------------------------------------------- BIDV HTML


def test_bidv_html_parses_table():
    ts = datetime(2026, 5, 14, 9, 30, tzinfo=VN_TZ)
    snap = parse_bidv_html(BIDV_HTML, quoted_at=ts)
    assert snap.bank is Bank.BIDV
    assert snap.quoted_at == ts
    codes = {q.currency for q in snap.quotes}
    assert codes == {Currency.USD, Currency.EUR, Currency.JPY}


def test_bidv_html_amounts_handle_thousand_separators():
    snap = parse_bidv_html(BIDV_HTML, quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ))
    usd = snap.get(Currency.USD)
    assert usd is not None
    assert usd.buy_cash_vnd == 24_800
    assert usd.buy_transfer_vnd == 24_830


def test_bidv_html_skips_garbage_currency_codes():
    snap = parse_bidv_html(BIDV_HTML, quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ))
    assert all(q.currency.value != "NOTACUR" for q in snap.quotes)


def test_bidv_html_handles_empty_table():
    empty = "<html><table></table></html>"
    snap = parse_bidv_html(empty, quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ))
    assert snap.quotes == ()


def test_bidv_html_bad_amount_raises():
    bad = """<table>
    <tr><th>Mã NT</th><th>Mua TM</th><th>Mua CK</th><th>Bán</th></tr>
    <tr><td>USD</td><td>WAT</td><td>24830</td><td>25180</td></tr>
    </table>"""
    with pytest.raises(ParseError) as e:
        parse_bidv_html(bad, quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ))
    assert e.value.field == "USD"


# -------------------------------------------------- Techcombank JSON


def test_tcb_json_parses_rates():
    snap = parse_techcombank_json(TCB_JSON)
    assert snap.bank is Bank.TCB
    assert {q.currency for q in snap.quotes} == {Currency.USD, Currency.EUR, Currency.JPY}


def test_tcb_json_datetime_with_offset_preserved():
    snap = parse_techcombank_json(TCB_JSON)
    # 09:30+07:00 in fixture.
    assert snap.quoted_at.utcoffset() is not None


def test_tcb_json_malformed_raises():
    with pytest.raises(ParseError) as e:
        parse_techcombank_json("not json")
    assert e.value.field == "root"


def test_tcb_json_missing_datetime_raises():
    bad = '{"data": {"rates": []}}'
    with pytest.raises(ParseError) as e:
        parse_techcombank_json(bad)
    assert e.value.field == "datetime"


def test_tcb_json_missing_rates_raises():
    bad = '{"data": {"datetime": "2026-05-14T09:30:00+07:00"}}'
    with pytest.raises(ParseError) as e:
        parse_techcombank_json(bad)
    assert e.value.field == "rates"


def test_tcb_json_skips_entries_with_wrong_types():
    bad_kind = """{"data":{"datetime":"2026-05-14T09:30:00+07:00","rates":["nope"]}}"""
    snap = parse_techcombank_json(bad_kind)
    assert snap.quotes == ()


def test_tcb_json_rejects_non_int_amounts():
    bad = """{"data":{"datetime":"2026-05-14T09:30:00+07:00","rates":[
        {"currency":"USD","buyCash":24800,"buyTransfer":"24830","sell":25180}
    ]}}"""
    with pytest.raises(ParseError):
        parse_techcombank_json(bad)


# -------------------------------------------------- generic CSV


def test_generic_csv_parses():
    ts = datetime(2026, 5, 14, 9, 30, tzinfo=VN_TZ)
    snap = parse_generic_csv(GENERIC_CSV, bank=Bank.VPB, quoted_at=ts)
    assert snap.bank is Bank.VPB
    assert {q.currency for q in snap.quotes} == {Currency.USD, Currency.EUR, Currency.JPY}


def test_generic_csv_missing_column_raises():
    bad = "currency,buy_cash,buy_transfer\nUSD,1,1\n"
    with pytest.raises(ParseError) as e:
        parse_generic_csv(bad, bank=Bank.VPB, quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ))
    assert e.value.field == "header"


def test_generic_csv_empty_returns_empty_snapshot():
    snap = parse_generic_csv("", bank=Bank.VPB, quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ))
    assert snap.quotes == ()


def test_generic_csv_bad_amount_raises():
    bad = "currency,buy_cash,buy_transfer,sell\nUSD,not-a-number,24830,25180\n"
    with pytest.raises(ParseError):
        parse_generic_csv(bad, bank=Bank.VPB, quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ))


def test_generic_csv_skips_unknown_currency():
    txt = "currency,buy_cash,buy_transfer,sell\nXYZ,1,2,3\nUSD,1,2,3\n"
    snap = parse_generic_csv(txt, bank=Bank.VPB, quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ))
    assert len(snap.quotes) == 1
    assert snap.quotes[0].currency is Currency.USD


def test_generic_csv_buy_cash_optional():
    txt = "currency,buy_cash,buy_transfer,sell\nUSD,,24830,25180\n"
    snap = parse_generic_csv(txt, bank=Bank.VPB, quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ))
    assert snap.quotes[0].buy_cash_vnd is None
