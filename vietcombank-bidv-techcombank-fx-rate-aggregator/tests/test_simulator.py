"""Simulator + anomaly-injection tests."""

from __future__ import annotations

import pytest

from fxagg.schema import Bank, Currency
from fxagg.simulator import generate
from fxagg.spread import AlertKind, analyze
from fxagg.storage import TimeSeriesStore


def test_generate_reproducible_with_seed():
    a = generate(seed=42, n_snapshots=2)
    b = generate(seed=42, n_snapshots=2)
    assert [(q.bank, q.currency, q.buy_transfer_vnd, q.sell_vnd) for q in a] == [
        (q.bank, q.currency, q.buy_transfer_vnd, q.sell_vnd) for q in b
    ]


def test_generate_different_seed_different_output():
    a = generate(seed=1, n_snapshots=1)
    b = generate(seed=2, n_snapshots=1)
    assert [q.buy_transfer_vnd for q in a] != [q.buy_transfer_vnd for q in b]


def test_generate_total_count_matches_grid():
    quotes = generate(
        banks=[Bank.VCB, Bank.BIDV, Bank.TCB],
        currencies=[Currency.USD, Currency.EUR],
        n_snapshots=4,
    )
    assert len(quotes) == 3 * 2 * 4


def test_generate_stale_drops_last_bank_last_snapshot():
    banks = [Bank.VCB, Bank.BIDV, Bank.TCB]
    quotes = generate(
        banks=banks,
        currencies=[Currency.USD],
        n_snapshots=2,
        inject_anomalies=["stale"],
    )
    # Last bank (TCB) should have only 1 snapshot (the older one).
    tcb = [q for q in quotes if q.bank is Bank.TCB]
    assert len(tcb) == 1


def test_generate_outlier_buy_triggers_alert_via_analyze():
    quotes = generate(
        banks=[Bank.VCB, Bank.BIDV, Bank.TCB, Bank.MB, Bank.VPB],
        currencies=[Currency.USD],
        n_snapshots=2,
        inject_anomalies=["outlier_buy"],
    )
    store = TimeSeriesStore()
    for q in quotes:
        store.append_quote(q)
    a = analyze(store.all_latest(Currency.USD), outlier_pct=1.0)
    assert AlertKind.BUY_OUTLIER in {al.kind for al in a.alerts}


def test_generate_inverted_triggers_alert():
    quotes = generate(
        banks=[Bank.VCB, Bank.BIDV, Bank.TCB, Bank.MB, Bank.VPB],
        currencies=[Currency.USD],
        n_snapshots=2,
        inject_anomalies=["inverted"],
    )
    store = TimeSeriesStore()
    for q in quotes:
        store.append_quote(q)
    a = analyze(store.all_latest(Currency.USD))
    assert AlertKind.INVERTED_SPREAD in {al.kind for al in a.alerts}


def test_generate_rejects_unknown_anomaly():
    with pytest.raises(ValueError):
        generate(
            banks=[Bank.VCB], currencies=[Currency.USD], n_snapshots=1, inject_anomalies=["meteor"]
        )


def test_generate_all_quotes_positive_amounts():
    quotes = generate(seed=99, n_snapshots=3)
    assert all(q.buy_transfer_vnd > 0 and q.sell_vnd > 0 for q in quotes)


def test_generate_spread_in_reasonable_range():
    """Synthetic spreads should sit in roughly the 0.5–1.2 % band.

    Integer truncation on small mid-prices (JPY mid ≈ 170) can push the realised
    spread up to ~1.8 %, so the upper bound is intentionally generous.
    """
    quotes = generate(seed=0, n_snapshots=2)
    for q in quotes:
        assert 0.4 < q.bid_ask_spread_pct < 2.0, q
