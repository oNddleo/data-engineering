"""JSONL codec round-trips."""

from __future__ import annotations

from datetime import date

import pytest

from vnstock.aggregator import aggregate_ticker_stats
from vnstock.anomaly import find_band_breaches
from vnstock.io_jsonl import (
    bar_from_dict,
    bar_to_dict,
    dump_anomalies,
    dump_bars,
    dump_orders,
    dump_stats,
    load_anomalies,
    load_bars,
    load_orders,
    load_stats,
    order_from_dict,
    order_to_dict,
)

from ._fixtures import make_bar, make_order


def test_bar_roundtrip() -> None:
    b = make_bar()
    assert bar_from_dict(bar_to_dict(b)) == b


def test_bar_dump_load_many() -> None:
    bars = [make_bar(date=date(2025, 1, 6 + i)) for i in range(5)]
    assert load_bars(dump_bars(bars)) == bars


def test_order_lo_roundtrip() -> None:
    o = make_order()
    assert order_from_dict(order_to_dict(o)) == o


def test_order_atc_roundtrip() -> None:
    from vnstock.schema import OrderKind

    o = make_order(kind=OrderKind.ATC, limit_price_vnd=0)
    assert order_from_dict(order_to_dict(o)) == o


def test_stats_roundtrip() -> None:
    bars = [make_bar(date=date(2025, 1, 6 + i)) for i in range(3)]
    stats = aggregate_ticker_stats(bars)
    out = load_stats(dump_stats(stats))
    assert out == stats


def test_anomaly_roundtrip() -> None:
    bar = make_bar(
        reference_price_vnd=50_000,
        open_vnd=50_000,
        high_vnd=55_000,
        low_vnd=50_000,
        close_vnd=54_000,
    )
    findings = find_band_breaches([bar])
    out = load_anomalies(dump_anomalies(findings))
    assert out == findings


def test_dump_skips_blank_lines() -> None:
    bars = [make_bar()]
    text = "\n\n" + dump_bars(bars) + "\n\n"
    assert load_bars(text) == bars


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_bars("[1, 2, 3]\n")


def test_load_rejects_wrong_type() -> None:
    """Type errors on decode surface as TypeError with a clear message."""
    bad = (
        '{"symbol": 1, "exchange": "HOSE", "date": "2025-01-06", '
        '"open_vnd": 100, "high_vnd": 100, "low_vnd": 100, "close_vnd": 100, '
        '"volume": 0, "reference_price_vnd": 100}\n'
    )
    with pytest.raises(TypeError, match="symbol"):
        load_bars(bad)


def test_dump_orders_empty() -> None:
    """Empty input → empty output."""
    assert load_orders(dump_orders([])) == []


def test_dump_orders_multiple() -> None:
    orders = [make_order(order_id=f"O-{i}", quantity=100 * (i + 1)) for i in range(3)]
    assert load_orders(dump_orders(orders)) == orders
