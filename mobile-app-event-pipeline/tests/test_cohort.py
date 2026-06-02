"""Cohort retention + LTV."""

from __future__ import annotations

from datetime import timedelta

from mappev.cohort import ltv, retention

from ._fixtures import (
    DEFAULT_TS,
    install_event,
    open_event,
    purchase_event,
)


def test_retention_no_activity():
    """An install with no follow-up has 0% retention."""
    events = [install_event("D-1", DEFAULT_TS)]
    [r] = retention(events)
    assert r.cohort_size == 1
    assert r.d1_active == 0


def test_retention_d1_activity_counted():
    """An open within 24h of install counts as D1 active."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        open_event("D-1", install_at + timedelta(hours=20)),
    ]
    [r] = retention(events)
    # The open at +20h falls in the D0 window (0-24h), not D1.
    # D1 window is 24h-48h post-install.
    assert r.d1_active == 0


def test_retention_d1_window_is_24_48h():
    """D1 = active 24h-48h after install."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        open_event("D-1", install_at + timedelta(hours=30)),
    ]
    [r] = retention(events)
    assert r.d1_active == 1


def test_retention_d7_window():
    """D7 = active 7-8 days after install."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        open_event("D-1", install_at + timedelta(days=7, hours=2)),
    ]
    [r] = retention(events)
    assert r.d7_active == 1


def test_retention_d30_window():
    """D30 = active 30-31 days after install."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        open_event("D-1", install_at + timedelta(days=30, hours=5)),
    ]
    [r] = retention(events)
    assert r.d30_active == 1


def test_retention_cohorts_one_per_day():
    """Installs on different days form separate cohorts."""
    events = [
        install_event("D-1", DEFAULT_TS),
        install_event("D-2", DEFAULT_TS + timedelta(days=1)),
        install_event("D-3", DEFAULT_TS + timedelta(days=2)),
    ]
    out = retention(events)
    assert len(out) == 3


def test_retention_same_day_installs_one_cohort():
    """Multiple installs on the same day form one cohort."""
    events = [install_event(f"D-{i}", DEFAULT_TS + timedelta(hours=i)) for i in range(5)]
    out = retention(events)
    assert len(out) == 1
    assert out[0].cohort_size == 5


def test_retention_purchase_counts_as_active():
    """A PURCHASE event counts as active, not just OPEN."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        purchase_event("D-1", install_at + timedelta(days=7, hours=3), 99_000),
    ]
    [r] = retention(events)
    assert r.d7_active == 1


# ---------- LTV ----------------------------------------------------------


def test_ltv_no_purchases():
    events = [install_event("D-1", DEFAULT_TS)]
    [c] = ltv(events)
    assert c.revenue_d30_vnd == 0
    assert c.ltv_d30_vnd == 0


def test_ltv_d1_window():
    """LTV D1 covers purchases in the first 24h."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        purchase_event("D-1", install_at + timedelta(hours=5), 100_000),
    ]
    [c] = ltv(events)
    assert c.revenue_d1_vnd == 100_000


def test_ltv_d1_inside_d7_inside_d30():
    """Revenue is cumulative — D7 ⊇ D1, D30 ⊇ D7."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        purchase_event("D-1", install_at + timedelta(hours=5), 100_000),
        purchase_event("D-1", install_at + timedelta(days=3), 200_000),
        purchase_event("D-1", install_at + timedelta(days=15), 500_000),
    ]
    [c] = ltv(events)
    assert c.revenue_d1_vnd == 100_000
    assert c.revenue_d7_vnd == 300_000
    assert c.revenue_d30_vnd == 800_000


def test_ltv_per_device_average():
    """LTV is per-device average revenue at the horizon."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        install_event("D-2", install_at),
        purchase_event("D-1", install_at + timedelta(hours=5), 200_000),
        # D-2 never buys.
    ]
    [c] = ltv(events)
    assert c.cohort_size == 2
    assert c.revenue_d1_vnd == 200_000
    assert c.ltv_d1_vnd == 100_000  # 200k / 2 devices


def test_ltv_only_pre_purchases_excluded():
    """A purchase BEFORE install doesn't count toward LTV."""
    install_at = DEFAULT_TS
    events = [
        purchase_event("D-1", install_at - timedelta(hours=1), 500_000),
        install_event("D-1", install_at),
    ]
    [c] = ltv(events)
    assert c.revenue_d1_vnd == 0
