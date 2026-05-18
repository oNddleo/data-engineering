"""Hypothesis properties — invariants of attribution + cohort + LTV + fraud."""

from __future__ import annotations

from datetime import timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mappev.attribute import attribute
from mappev.cohort import ltv, retention
from mappev.fraud import find_click_injection
from mappev.schema import Attribution, EventKind
from mappev.simulator import generate

from ._fixtures import (
    DEFAULT_TS,
    click_event,
    impression_event,
    install_event,
    purchase_event,
)

# ---------- attribute --------------------------------------------------------


@given(lag_hours=st.integers(min_value=1, max_value=24 * 7))
@settings(max_examples=40)
def test_property_click_within_window_attributes(lag_hours: int) -> None:
    """A single click within 7d → attribution is non-organic with that source."""
    install_at = DEFAULT_TS + timedelta(days=10)
    events = [
        click_event("D-1", install_at - timedelta(hours=lag_hours), source="facebook"),
        install_event("D-1", install_at),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "facebook"
    assert a.attribution_event_id is not None
    assert a.attribution_lag_seconds == lag_hours * 3_600


@given(lag_days=st.integers(min_value=8, max_value=60))
@settings(max_examples=20)
def test_property_click_outside_window_is_organic(lag_days: int) -> None:
    """A click more than 7d before install does NOT attribute."""
    install_at = DEFAULT_TS + timedelta(days=lag_days + 5)
    events = [
        click_event("D-1", install_at - timedelta(days=lag_days), source="facebook"),
        install_event("D-1", install_at),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "organic"


@given(view_hours=st.integers(min_value=25, max_value=72))
@settings(max_examples=20)
def test_property_impression_past_24h_is_organic(view_hours: int) -> None:
    """An impression more than 24h before install does NOT attribute."""
    install_at = DEFAULT_TS + timedelta(days=4)
    events = [
        impression_event("D-1", install_at - timedelta(hours=view_hours)),
        install_event("D-1", install_at),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "organic"


@given(
    n_devices=st.integers(min_value=5, max_value=80),
    n_days=st.integers(min_value=5, max_value=30),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_property_attribute_lag_non_negative(
    n_devices: int,
    n_days: int,
    seed: int,
) -> None:
    """Every attribution has a non-negative lag (the schema enforces it,
    but the function must respect it too)."""
    events = generate(n_devices=n_devices, n_days=n_days, seed=seed)
    attributions = attribute(events)
    for a in attributions:
        assert a.attribution_lag_seconds >= 0


@given(
    n_devices=st.integers(min_value=5, max_value=60),
    n_days=st.integers(min_value=5, max_value=20),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_property_attribute_one_per_install(
    n_devices: int,
    n_days: int,
    seed: int,
) -> None:
    """attribute() returns exactly one Attribution per INSTALL event."""
    events = generate(n_devices=n_devices, n_days=n_days, seed=seed)
    installs = [e for e in events if e.kind is EventKind.INSTALL]
    attributions = attribute(events)
    assert len(attributions) == len(installs)
    assert {a.device_id for a in attributions} == {i.device_id for i in installs}


@given(
    n_devices=st.integers(min_value=5, max_value=40),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_attribute_sorted_by_install_then_device(
    n_devices: int,
    seed: int,
) -> None:
    """Output is sorted by (install_at, device_id) for stable diffs."""
    events = generate(n_devices=n_devices, n_days=15, seed=seed)
    out = attribute(events)
    keys = [(a.install_at, a.device_id) for a in out]
    assert keys == sorted(keys)


# ---------- cohort -----------------------------------------------------------


@given(
    n_devices=st.integers(min_value=5, max_value=60),
    n_days=st.integers(min_value=5, max_value=20),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_cohort_sizes_sum_to_install_count(
    n_devices: int,
    n_days: int,
    seed: int,
) -> None:
    """sum(cohort_size) == # of INSTALL events."""
    events = generate(n_devices=n_devices, n_days=n_days, seed=seed)
    installs = sum(1 for e in events if e.kind is EventKind.INSTALL)
    cohorts = retention(events)
    assert sum(c.cohort_size for c in cohorts) == installs


@given(
    n_devices=st.integers(min_value=5, max_value=60),
    n_days=st.integers(min_value=5, max_value=20),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_d1_active_le_d7_active_le_d30_active_loose(
    n_devices: int,
    n_days: int,
    seed: int,
) -> None:
    """In a CUMULATIVE-window definition we'd have d1<=d7<=d30, but here
    each window is disjoint — so all we can promise is each is in
    [0, cohort_size]."""
    events = generate(n_devices=n_devices, n_days=n_days, seed=seed)
    for c in retention(events):
        assert 0 <= c.d1_active <= c.cohort_size
        assert 0 <= c.d7_active <= c.cohort_size
        assert 0 <= c.d30_active <= c.cohort_size


@given(
    n_devices=st.integers(min_value=5, max_value=60),
    n_days=st.integers(min_value=5, max_value=20),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_ltv_cumulative(
    n_devices: int,
    n_days: int,
    seed: int,
) -> None:
    """revenue_d1 <= revenue_d7 <= revenue_d30 (cumulative-window LTV)."""
    events = generate(n_devices=n_devices, n_days=n_days, seed=seed)
    for c in ltv(events):
        assert c.revenue_d1_vnd <= c.revenue_d7_vnd <= c.revenue_d30_vnd


@given(amount=st.integers(min_value=1_000, max_value=10_000_000))
@settings(max_examples=30)
def test_property_single_purchase_within_d1_counts(amount: int) -> None:
    """One purchase within 24h of install → revenue_d1 equals that amount."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        purchase_event("D-1", install_at + timedelta(hours=3), amount),
    ]
    [c] = ltv(events)
    assert c.revenue_d1_vnd == amount
    assert c.revenue_d7_vnd == amount  # cumulative


# ---------- fraud ------------------------------------------------------------


@given(
    n_devices=st.integers(min_value=10, max_value=40),
    threshold=st.integers(min_value=2, max_value=60),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_click_injection_all_findings_have_lag_below_threshold(
    n_devices: int,
    threshold: int,
) -> None:
    """When we build attributions whose lag is uniformly below ``threshold``,
    every resulting (source, campaign) bucket with >=3 devices is flagged."""
    attrs = [
        Attribution(
            device_id=f"D-{i}",
            install_at=DEFAULT_TS,
            attributed_source="badnet",
            attributed_campaign="evil",
            attribution_event_id=f"C-{i}",
            attribution_lag_seconds=0,  # always strictly < threshold
        )
        for i in range(n_devices)
    ]
    findings = find_click_injection(attrs, min_lag_seconds=threshold)
    assert len(findings) == 1
    assert findings[0].devices_affected == n_devices
