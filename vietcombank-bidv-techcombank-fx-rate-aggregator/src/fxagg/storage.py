"""Time-series store for FX quotes.

In-memory ``dict[(Bank, Currency)] → list[Quote]`` with quotes
kept sorted by ``quoted_at``. Optional JSONL append-only persistence
so the store can be rehydrated across scrapes.

Choice of data structure: a single dict keyed by (bank, currency)
with a Python ``list`` per series. For the scale this monitor runs
at — 10 banks × 11 currencies × every-5-min — even a year of data
is < 1.2M points total, fits in memory trivially, and ``bisect``
gives us O(log n) range queries. If you ever go bigger you replace
this module with a real TSDB; the rest of the codebase doesn't care.
"""

from __future__ import annotations

import bisect
import json
from datetime import datetime
from typing import TYPE_CHECKING

from fxagg.schema import VN_TZ, Bank, Currency, Quote, Snapshot

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path


class TimeSeriesStore:
    """A small in-memory TSDB scoped to FX quotes."""

    def __init__(self) -> None:
        self._series: dict[tuple[Bank, Currency], list[Quote]] = {}

    @property
    def series_count(self) -> int:
        return len(self._series)

    def append_quote(self, quote: Quote) -> None:
        """Insert one quote, keeping the per-series list sorted by ``quoted_at``.

        Idempotent: an exact-duplicate quote (same bank, currency,
        quoted_at, all amounts) is silently dropped.
        """
        key = (quote.bank, quote.currency)
        series = self._series.setdefault(key, [])
        times = [q.quoted_at for q in series]
        idx = bisect.bisect_left(times, quote.quoted_at)
        if idx < len(series) and series[idx] == quote:
            return
        series.insert(idx, quote)

    def append_snapshot(self, snapshot: Snapshot) -> int:
        n = 0
        for q in snapshot.quotes:
            self.append_quote(q)
            n += 1
        return n

    def latest(self, bank: Bank, currency: Currency) -> Quote | None:
        series = self._series.get((bank, currency))
        if not series:
            return None
        return series[-1]

    def history(
        self,
        bank: Bank,
        currency: Currency,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Quote]:
        series = self._series.get((bank, currency), [])
        if since is None and until is None:
            return list(series)
        lo = 0 if since is None else bisect.bisect_left([q.quoted_at for q in series], since)
        hi = (
            len(series)
            if until is None
            else bisect.bisect_right([q.quoted_at for q in series], until)
        )
        return series[lo:hi]

    def all_latest(self, currency: Currency) -> dict[Bank, Quote]:
        """Latest quote per bank for a given currency. Useful for spread analysis."""
        out: dict[Bank, Quote] = {}
        for (bank, c), series in self._series.items():
            if c is currency and series:
                out[bank] = series[-1]
        return out

    def as_of(self, currency: Currency, at: datetime) -> dict[Bank, Quote]:
        """Each bank's *most recent* quote not after ``at``."""
        out: dict[Bank, Quote] = {}
        for (bank, c), series in self._series.items():
            if c is not currency or not series:
                continue
            times = [q.quoted_at for q in series]
            idx = bisect.bisect_right(times, at)
            if idx > 0:
                out[bank] = series[idx - 1]
        return out

    def quotes(self) -> Iterator[Quote]:
        """Yield every quote in (bank, currency, quoted_at) order."""
        for key in sorted(self._series.keys(), key=lambda k: (k[0].value, k[1].value)):
            yield from self._series[key]


# ---------------------------------------------------------------------------
# JSONL persistence


def quote_to_dict(q: Quote) -> dict[str, object]:
    return {
        "bank": q.bank.value,
        "currency": q.currency.value,
        "buy_transfer_vnd": q.buy_transfer_vnd,
        "sell_vnd": q.sell_vnd,
        "quoted_at": q.quoted_at.isoformat(),
        "buy_cash_vnd": q.buy_cash_vnd,
    }


def quote_from_dict(d: dict[str, object]) -> Quote:
    bank_raw = d["bank"]
    cur_raw = d["currency"]
    bt_raw = d["buy_transfer_vnd"]
    sell_raw = d["sell_vnd"]
    qa_raw = d["quoted_at"]
    if not isinstance(bank_raw, str) or not isinstance(cur_raw, str):
        raise TypeError("bank/currency must be strings")
    if not isinstance(bt_raw, int) or isinstance(bt_raw, bool):
        raise TypeError("buy_transfer_vnd must be int")
    if not isinstance(sell_raw, int) or isinstance(sell_raw, bool):
        raise TypeError("sell_vnd must be int")
    if not isinstance(qa_raw, str):
        raise TypeError("quoted_at must be ISO-8601 string")
    quoted_at = datetime.fromisoformat(qa_raw)
    if quoted_at.tzinfo is None:
        quoted_at = quoted_at.replace(tzinfo=VN_TZ)
    bc_raw = d.get("buy_cash_vnd")
    buy_cash = bc_raw if isinstance(bc_raw, int) and not isinstance(bc_raw, bool) else None
    return Quote(
        bank=Bank(bank_raw),
        currency=Currency(cur_raw),
        buy_transfer_vnd=bt_raw,
        sell_vnd=sell_raw,
        quoted_at=quoted_at,
        buy_cash_vnd=buy_cash,
    )


def dump_quotes(quotes: Iterable[Quote]) -> str:
    return "\n".join(json.dumps(quote_to_dict(q), ensure_ascii=False) for q in quotes) + "\n"


def load_quotes(text: str) -> Iterator[Quote]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield quote_from_dict(json.loads(line))


def save_store(store: TimeSeriesStore, path: Path) -> None:
    path.write_text(dump_quotes(store.quotes()), encoding="utf-8")


def load_store(path: Path) -> TimeSeriesStore:
    store = TimeSeriesStore()
    for q in load_quotes(path.read_text(encoding="utf-8")):
        store.append_quote(q)
    return store


__all__ = [
    "TimeSeriesStore",
    "dump_quotes",
    "load_quotes",
    "load_store",
    "quote_from_dict",
    "quote_to_dict",
    "save_store",
]
