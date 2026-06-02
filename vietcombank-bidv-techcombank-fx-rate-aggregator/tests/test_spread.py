"""Cross-bank spread analyzer + alert tests."""

from __future__ import annotations

import pytest

from fxagg.schema import Bank, Currency
from fxagg.spread import AlertKind, Severity, analyze

from ._fixtures import make_quote, t_at


def _five_bank_quotes():
    return {
        Bank.VCB: make_quote(bank=Bank.VCB, buy_transfer=25_000, sell=25_200, quoted_at=t_at(0)),
        Bank.BIDV: make_quote(bank=Bank.BIDV, buy_transfer=25_020, sell=25_220, quoted_at=t_at(0)),
        Bank.TCB: make_quote(bank=Bank.TCB, buy_transfer=25_010, sell=25_210, quoted_at=t_at(0)),
        Bank.MB: make_quote(bank=Bank.MB, buy_transfer=24_990, sell=25_190, quoted_at=t_at(0)),
        Bank.VPB: make_quote(bank=Bank.VPB, buy_transfer=25_005, sell=25_205, quoted_at=t_at(0)),
    }


def test_analyze_empty_input_returns_zero_medians():
    a = analyze({})
    assert a.median_buy_transfer == 0
    assert a.alerts == ()


def test_analyze_rejects_mixed_currencies():
    qs = {
        Bank.VCB: make_quote(currency=Currency.USD),
        Bank.BIDV: make_quote(
            bank=Bank.BIDV, currency=Currency.EUR, buy_transfer=27_000, sell=27_200, buy_cash=26_900
        ),
    }
    with pytest.raises(ValueError):
        analyze(qs)


def test_analyze_clean_set_yields_no_alerts():
    a = analyze(_five_bank_quotes(), outlier_pct=1.0)
    assert a.alerts == ()
    # Sorted buys [24990,25000,25005,25010,25020] → median 25005.
    assert a.median_buy_transfer == 25_005
    # Sorted sells [25190,25200,25205,25210,25220] → median 25205.
    assert a.median_sell == 25_205


def test_analyze_detects_buy_outlier():
    qs = _five_bank_quotes()
    # VPB's buy is ~5 % above peer median. Bump sell to match so the row is
    # NOT inverted — otherwise INVERTED_SPREAD short-circuits the outlier rule.
    qs[Bank.VPB] = make_quote(bank=Bank.VPB, buy_transfer=26_300, sell=26_500, quoted_at=t_at(0))
    a = analyze(qs, outlier_pct=1.0)
    kinds = {al.kind for al in a.alerts}
    assert AlertKind.BUY_OUTLIER in kinds


def test_analyze_detects_sell_outlier():
    qs = _five_bank_quotes()
    qs[Bank.VPB] = make_quote(bank=Bank.VPB, buy_transfer=25_005, sell=26_500, quoted_at=t_at(0))
    a = analyze(qs, outlier_pct=1.0)
    kinds = {al.kind for al in a.alerts}
    assert AlertKind.SELL_OUTLIER in kinds


def test_analyze_detects_inverted_spread():
    qs = _five_bank_quotes()
    qs[Bank.MB] = make_quote(bank=Bank.MB, buy_transfer=25_200, sell=25_000, quoted_at=t_at(0))
    a = analyze(qs)
    kinds = {al.kind for al in a.alerts}
    assert AlertKind.INVERTED_SPREAD in kinds


def test_inverted_spread_alert_severity_is_crit():
    qs = _five_bank_quotes()
    qs[Bank.MB] = make_quote(bank=Bank.MB, buy_transfer=25_200, sell=25_000, quoted_at=t_at(0))
    a = analyze(qs)
    inverted = [al for al in a.alerts if al.kind is AlertKind.INVERTED_SPREAD]
    assert inverted and inverted[0].severity is Severity.CRIT


def test_inverted_row_does_not_also_fire_outlier():
    """An inverted spread short-circuits — no outlier alert for that bank."""
    qs = _five_bank_quotes()
    qs[Bank.MB] = make_quote(bank=Bank.MB, buy_transfer=99_999, sell=1, quoted_at=t_at(0))
    a = analyze(qs)
    mb_alerts = [al for al in a.alerts if al.bank is Bank.MB]
    assert len(mb_alerts) == 1
    assert mb_alerts[0].kind is AlertKind.INVERTED_SPREAD


def test_outlier_pct_threshold_is_inclusive():
    qs = _five_bank_quotes()
    # Note: bumping VPB shifts the median too. With VPB=25,300 the new buys
    # are [24990, 25000, 25010, 25020, 25300] → median 25,010. VPB's deviation
    # is (25,300 − 25,010) / 25,010 ≈ 1.16 %, comfortably above the 1 % bar.
    qs[Bank.VPB] = make_quote(bank=Bank.VPB, buy_transfer=25_300, sell=25_500, quoted_at=t_at(0))
    a = analyze(qs, outlier_pct=1.0)
    kinds = {al.kind for al in a.alerts}
    assert AlertKind.BUY_OUTLIER in kinds


def test_stale_quote_alert_with_reference_time():
    qs = _five_bank_quotes()
    qs[Bank.MB] = make_quote(bank=Bank.MB, buy_transfer=25_005, sell=25_205, quoted_at=t_at(-120))
    a = analyze(qs, stale_threshold_min=30, reference_time=t_at(0))
    stale = [al for al in a.alerts if al.kind is AlertKind.STALE_QUOTE]
    assert any(al.bank is Bank.MB for al in stale)


def test_stale_quote_skipped_when_no_reference_time():
    qs = _five_bank_quotes()
    qs[Bank.MB] = make_quote(bank=Bank.MB, buy_transfer=25_005, sell=25_205, quoted_at=t_at(-120))
    a = analyze(qs, stale_threshold_min=30)
    assert all(al.kind is not AlertKind.STALE_QUOTE for al in a.alerts)


def test_analyze_small_set_skips_outlier_detection():
    """With < 3 banks, median is meaningless — outlier rule must not fire."""
    qs = {
        Bank.VCB: make_quote(bank=Bank.VCB, buy_transfer=25_000, sell=25_200, quoted_at=t_at(0)),
        Bank.BIDV: make_quote(bank=Bank.BIDV, buy_transfer=30_000, sell=30_200, quoted_at=t_at(0)),
    }
    a = analyze(qs, outlier_pct=1.0)
    assert all(al.kind not in (AlertKind.BUY_OUTLIER, AlertKind.SELL_OUTLIER) for al in a.alerts)


def test_analyze_alerts_sorted_for_stable_diff():
    qs = _five_bank_quotes()
    qs[Bank.VCB] = make_quote(bank=Bank.VCB, buy_transfer=26_500, sell=25_200, quoted_at=t_at(0))
    qs[Bank.MB] = make_quote(bank=Bank.MB, buy_transfer=25_200, sell=25_000, quoted_at=t_at(0))
    a = analyze(qs, outlier_pct=1.0)
    keys = [(al.kind.value, al.bank.value) for al in a.alerts]
    assert keys == sorted(keys)


def test_analyze_deviation_pct_carried_on_alert():
    qs = _five_bank_quotes()
    # buy 26,500 is +5.97 % above median 25,005; sell 26,700 keeps row non-inverted.
    qs[Bank.VPB] = make_quote(bank=Bank.VPB, buy_transfer=26_500, sell=26_700, quoted_at=t_at(0))
    a = analyze(qs, outlier_pct=1.0)
    buy_outliers = [al for al in a.alerts if al.kind is AlertKind.BUY_OUTLIER]
    assert buy_outliers and buy_outliers[0].deviation_pct is not None
    assert buy_outliers[0].deviation_pct > 1.0
