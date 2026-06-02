"""Schema invariants."""

from __future__ import annotations

from datetime import datetime

import pytest

from mappev.schema import CohortLTV, CohortRetention, EventKind

from ._fixtures import DEFAULT_TS, make_event


def test_event_kind_six_values():
    assert {k.value for k in EventKind} == {
        "CLICK",
        "IMPRESSION",
        "INSTALL",
        "OPEN",
        "IN_APP",
        "PURCHASE",
    }


def test_event_rejects_empty_device_id():
    with pytest.raises(ValueError):
        make_event(device_id="")


def test_event_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_event(occurred_at=datetime(2026, 5, 17, 9, 0))


def test_event_rejects_negative_revenue():
    with pytest.raises(ValueError):
        make_event(kind=EventKind.PURCHASE, revenue_vnd=-1)


def test_in_app_event_requires_name():
    with pytest.raises(ValueError, match="in_app_event_name"):
        make_event(kind=EventKind.IN_APP, in_app_event_name="")


def test_non_in_app_rejects_name():
    """An OPEN event can't have an in_app_event_name."""
    with pytest.raises(ValueError, match="in_app_event_name"):
        make_event(kind=EventKind.OPEN, in_app_event_name="level_up")


def test_revenue_only_on_purchase():
    """An OPEN with revenue is rejected."""
    with pytest.raises(ValueError, match="revenue_vnd"):
        make_event(kind=EventKind.OPEN, revenue_vnd=10_000)


def test_purchase_can_have_revenue():
    """A PURCHASE with revenue is fine."""
    e = make_event(kind=EventKind.PURCHASE, revenue_vnd=99_000)
    assert e.revenue_vnd == 99_000


def test_purchase_can_have_zero_revenue():
    """A zero-amount PURCHASE is still legal (free promo, refunds)."""
    e = make_event(kind=EventKind.PURCHASE, revenue_vnd=0)
    assert e.revenue_vnd == 0


def test_event_rejects_empty_source():
    with pytest.raises(ValueError, match="source"):
        make_event(source="")


def test_cohort_retention_d1_pct_zero_for_empty_cohort():
    r = CohortRetention(
        cohort_date="2026-05-17",
        cohort_size=0,
        d1_active=0,
        d7_active=0,
        d30_active=0,
    )
    assert r.d1_pct == 0.0


def test_cohort_retention_d1_pct_computed():
    r = CohortRetention(
        cohort_date="2026-05-17",
        cohort_size=10,
        d1_active=8,
        d7_active=5,
        d30_active=2,
    )
    assert r.d1_pct == 80.0
    assert r.d7_pct == 50.0
    assert r.d30_pct == 20.0


def test_cohort_ltv_d30_floor_divides():
    c = CohortLTV(
        cohort_date="2026-05-17",
        cohort_size=3,
        revenue_d1_vnd=300,
        revenue_d7_vnd=600,
        revenue_d30_vnd=1_000,
    )
    assert c.ltv_d1_vnd == 100
    assert c.ltv_d7_vnd == 200
    assert c.ltv_d30_vnd == 333


def test_cohort_ltv_zero_for_empty_cohort():
    c = CohortLTV(
        cohort_date="2026-05-17",
        cohort_size=0,
        revenue_d1_vnd=0,
        revenue_d7_vnd=0,
        revenue_d30_vnd=0,
    )
    assert c.ltv_d30_vnd == 0


def test_default_event_is_legal():
    """Sanity — the fixture's default event passes validation."""
    e = make_event()
    assert e.event_id == "E-0001"
    assert e.occurred_at == DEFAULT_TS
