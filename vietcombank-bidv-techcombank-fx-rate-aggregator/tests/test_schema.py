"""Quote / Snapshot invariants."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fxagg.schema import VN_TZ, Bank, Currency, Snapshot

from ._fixtures import make_quote


def test_currency_enum_includes_top10_vn_currencies():
    codes = {c.value for c in Currency}
    for need in ("USD", "EUR", "JPY", "GBP", "AUD", "SGD", "CNY", "KRW", "THB"):
        assert need in codes, need


def test_bank_enum_has_top10_codes():
    codes = {b.value for b in Bank}
    assert {"VCB", "BIDV", "TCB", "MB", "VPB", "ACB", "VTB"} <= codes


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_quote_happy_path():
    q = make_quote(buy_transfer=24_830, sell=25_180)
    assert q.bid_ask_spread_vnd == 350
    assert 1.3 < q.bid_ask_spread_pct < 1.5


def test_quote_rejects_non_positive_buy():
    with pytest.raises(ValueError):
        make_quote(buy_transfer=0)
    with pytest.raises(ValueError):
        make_quote(buy_transfer=-1)


def test_quote_rejects_non_positive_sell():
    with pytest.raises(ValueError):
        make_quote(sell=0)


def test_quote_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_quote(quoted_at=datetime(2026, 5, 14))


def test_quote_accepts_none_buy_cash():
    q = make_quote(buy_cash=None)
    assert q.buy_cash_vnd is None


def test_quote_rejects_non_positive_buy_cash():
    with pytest.raises(ValueError):
        make_quote(buy_cash=0)


def test_quote_inverted_spread_is_negative():
    q = make_quote(buy_transfer=25_200, sell=25_000)
    assert q.bid_ask_spread_vnd == -200
    assert q.bid_ask_spread_pct < 0


def test_quote_utc_datetime_accepted():
    q = make_quote(quoted_at=datetime(2026, 5, 14, 2, 0, tzinfo=timezone.utc))
    assert q.quoted_at.tzinfo is not None


def test_snapshot_get_finds_currency():
    q_usd = make_quote(currency=Currency.USD)
    q_eur = make_quote(currency=Currency.EUR, buy_transfer=27_000, sell=27_300, buy_cash=26_900)
    s = Snapshot(bank=Bank.VCB, quoted_at=q_usd.quoted_at, quotes=(q_usd, q_eur))
    assert s.get(Currency.USD) is q_usd
    assert s.get(Currency.EUR) is q_eur
    assert s.get(Currency.JPY) is None


def test_snapshot_rejects_mixed_banks():
    q = make_quote(bank=Bank.BIDV)
    with pytest.raises(ValueError):
        Snapshot(bank=Bank.VCB, quoted_at=q.quoted_at, quotes=(q,))


def test_snapshot_rejects_naive_datetime():
    with pytest.raises(ValueError):
        Snapshot(bank=Bank.VCB, quoted_at=datetime(2026, 5, 14), quotes=())
