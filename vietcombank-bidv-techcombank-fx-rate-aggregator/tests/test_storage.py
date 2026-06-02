"""TimeSeriesStore + JSONL persistence tests."""

from __future__ import annotations

from pathlib import Path

from fxagg.schema import Bank, Currency, Snapshot
from fxagg.storage import (
    TimeSeriesStore,
    dump_quotes,
    load_quotes,
    load_store,
    quote_from_dict,
    quote_to_dict,
    save_store,
)

from ._fixtures import make_quote, t_at


def test_append_quote_and_latest():
    s = TimeSeriesStore()
    q = make_quote()
    s.append_quote(q)
    assert s.latest(Bank.VCB, Currency.USD) == q


def test_append_quote_sorts_by_time():
    s = TimeSeriesStore()
    s.append_quote(make_quote(quoted_at=t_at(10), buy_transfer=25_100, sell=25_200))
    s.append_quote(make_quote(quoted_at=t_at(0), buy_transfer=25_000, sell=25_100))
    s.append_quote(make_quote(quoted_at=t_at(20), buy_transfer=25_200, sell=25_300))
    hist = s.history(Bank.VCB, Currency.USD)
    assert [q.quoted_at for q in hist] == [t_at(0), t_at(10), t_at(20)]


def test_append_quote_is_idempotent_on_exact_duplicate():
    s = TimeSeriesStore()
    q = make_quote(quoted_at=t_at(0))
    s.append_quote(q)
    s.append_quote(q)
    assert len(s.history(Bank.VCB, Currency.USD)) == 1


def test_append_snapshot_inserts_all_quotes():
    quotes = (
        make_quote(currency=Currency.USD),
        make_quote(currency=Currency.EUR, buy_transfer=26_000, sell=27_000, buy_cash=25_900),
    )
    snap = Snapshot(bank=Bank.VCB, quoted_at=quotes[0].quoted_at, quotes=quotes)
    s = TimeSeriesStore()
    n = s.append_snapshot(snap)
    assert n == 2
    assert s.latest(Bank.VCB, Currency.USD) is not None
    assert s.latest(Bank.VCB, Currency.EUR) is not None


def test_latest_returns_none_for_missing_series():
    assert TimeSeriesStore().latest(Bank.VCB, Currency.USD) is None


def test_history_with_since_filter():
    s = TimeSeriesStore()
    for i in range(5):
        s.append_quote(make_quote(quoted_at=t_at(i * 10)))
    out = s.history(Bank.VCB, Currency.USD, since=t_at(15))
    assert [q.quoted_at for q in out] == [t_at(20), t_at(30), t_at(40)]


def test_history_with_until_filter():
    s = TimeSeriesStore()
    for i in range(5):
        s.append_quote(make_quote(quoted_at=t_at(i * 10)))
    out = s.history(Bank.VCB, Currency.USD, until=t_at(20))
    assert [q.quoted_at for q in out] == [t_at(0), t_at(10), t_at(20)]


def test_all_latest_returns_one_per_bank():
    s = TimeSeriesStore()
    s.append_quote(make_quote(bank=Bank.VCB, quoted_at=t_at(0)))
    s.append_quote(make_quote(bank=Bank.BIDV, quoted_at=t_at(1)))
    s.append_quote(make_quote(bank=Bank.TCB, quoted_at=t_at(2)))
    latest = s.all_latest(Currency.USD)
    assert set(latest.keys()) == {Bank.VCB, Bank.BIDV, Bank.TCB}


def test_as_of_returns_most_recent_not_after():
    s = TimeSeriesStore()
    for i in range(5):
        s.append_quote(make_quote(quoted_at=t_at(i * 10)))
    asof = s.as_of(Currency.USD, t_at(25))
    assert asof[Bank.VCB].quoted_at == t_at(20)


def test_quote_round_trips_through_dict():
    q = make_quote(buy_transfer=24_830, sell=25_180)
    assert quote_from_dict(quote_to_dict(q)) == q


def test_dump_load_quotes_round_trip():
    quotes = [make_quote(buy_transfer=25_000 + i, sell=25_200 + i) for i in range(5)]
    out = dump_quotes(quotes)
    loaded = list(load_quotes(out))
    assert loaded == quotes


def test_save_load_store_round_trip(tmp_path: Path):
    s = TimeSeriesStore()
    for i in range(5):
        s.append_quote(make_quote(quoted_at=t_at(i * 5), buy_transfer=25_000 + i, sell=25_200 + i))
    p = tmp_path / "store.jsonl"
    save_store(s, p)
    s2 = load_store(p)
    assert s2.history(Bank.VCB, Currency.USD) == s.history(Bank.VCB, Currency.USD)


def test_series_count_reflects_unique_series():
    s = TimeSeriesStore()
    s.append_quote(make_quote(bank=Bank.VCB))
    s.append_quote(make_quote(bank=Bank.BIDV))
    s.append_quote(
        make_quote(
            bank=Bank.VCB, currency=Currency.EUR, buy_transfer=27_000, sell=27_300, buy_cash=26_900
        )
    )
    assert s.series_count == 3
