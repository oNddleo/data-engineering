"""Click-injection + install-spam detection."""

from __future__ import annotations

from datetime import timedelta

import pytest

from mappev.fraud import (
    FraudKind,
    find_click_injection,
    find_install_spam,
)
from mappev.schema import Attribution

from ._fixtures import (
    DEFAULT_TS,
    install_event,
    open_event,
    purchase_event,
)


def _attr(
    device_id: str,
    source: str = "facebook",
    campaign: str = "vn_promo",
    lag: int = 1_000,
    event_id: str | None = "C-1",
) -> Attribution:
    return Attribution(
        device_id=device_id,
        install_at=DEFAULT_TS,
        attributed_source=source,
        attributed_campaign=campaign,
        attribution_event_id=event_id,
        attribution_lag_seconds=lag,
    )


# ---------- click injection ---------------------------------------------------


def test_click_injection_below_threshold_flagged():
    """Three devices with lag < 20s on the same source = a finding."""
    attrs = [_attr(f"D-{i}", source="dodgy", campaign="x", lag=5) for i in range(3)]
    findings = find_click_injection(attrs)
    assert len(findings) == 1
    f = findings[0]
    assert f.kind is FraudKind.CLICK_INJECTION
    assert f.source == "dodgy:x"
    assert f.devices_affected == 3


def test_click_injection_organic_skipped():
    """Organic attributions (event_id=None) are not eligible for injection."""
    attrs = [
        Attribution(
            device_id=f"D-{i}",
            install_at=DEFAULT_TS,
            attributed_source="organic",
            attributed_campaign="",
            attribution_event_id=None,
            attribution_lag_seconds=0,
        )
        for i in range(5)
    ]
    assert find_click_injection(attrs) == []


def test_click_injection_above_threshold_ignored():
    """Lag >= threshold is plausible — not flagged."""
    attrs = [_attr(f"D-{i}", source="facebook", lag=200) for i in range(5)]
    assert find_click_injection(attrs) == []


def test_click_injection_under_three_devices_skipped():
    """Two suspicious devices on a source isn't enough — could be noise."""
    attrs = [_attr(f"D-{i}", source="small", lag=2) for i in range(2)]
    assert find_click_injection(attrs) == []


def test_click_injection_multiple_sources_independent():
    """Each (source, campaign) is judged independently."""
    attrs = [
        *(_attr(f"DA-{i}", source="srcA", campaign="x", lag=3) for i in range(4)),
        *(_attr(f"DB-{i}", source="srcB", campaign="y", lag=3) for i in range(5)),
    ]
    findings = find_click_injection(attrs)
    assert len(findings) == 2
    # Sorted by -devices_affected, then source — srcB first (5 > 4).
    assert findings[0].source == "srcB:y"
    assert findings[1].source == "srcA:x"


def test_click_injection_custom_threshold():
    """Threshold is configurable."""
    attrs = [_attr(f"D-{i}", source="x", lag=50) for i in range(3)]
    assert find_click_injection(attrs) == []
    findings = find_click_injection(attrs, min_lag_seconds=60)
    assert len(findings) == 1


def test_click_injection_rejects_invalid_threshold():
    with pytest.raises(ValueError, match="must be > 0"):
        find_click_injection([], min_lag_seconds=0)


# ---------- install spam ------------------------------------------------------


def test_install_spam_low_d1_flagged():
    """A source with 0% D1 retention and >= min_installs gets flagged."""
    devices = [f"DS-{i}" for i in range(10)]
    events = [install_event(d, DEFAULT_TS) for d in devices]
    attrs = [
        Attribution(
            device_id=d,
            install_at=DEFAULT_TS,
            attributed_source="spammy",
            attributed_campaign="farm",
            attribution_event_id="C-x",
            attribution_lag_seconds=600,
        )
        for d in devices
    ]
    findings = find_install_spam(events, attrs, min_installs=5, min_d1_rate_pct=5)
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.INSTALL_SPAM
    assert findings[0].source == "spammy:farm"
    assert findings[0].devices_affected == 10


def test_install_spam_healthy_d1_not_flagged():
    """A source with >= 5% D1 retention passes."""
    devices = [f"DH-{i}" for i in range(10)]
    events = [install_event(d, DEFAULT_TS) for d in devices]
    # Every device opens within 24h -> 100% D1.
    events.extend(open_event(d, DEFAULT_TS + timedelta(hours=2)) for d in devices)
    attrs = [
        Attribution(
            device_id=d,
            install_at=DEFAULT_TS,
            attributed_source="facebook",
            attributed_campaign="vn",
            attribution_event_id="C-x",
            attribution_lag_seconds=600,
        )
        for d in devices
    ]
    assert find_install_spam(events, attrs) == []


def test_install_spam_below_min_installs_skipped():
    """A source with fewer than ``min_installs`` is too small to judge."""
    devices = [f"DT-{i}" for i in range(3)]
    events = [install_event(d, DEFAULT_TS) for d in devices]
    attrs = [
        Attribution(
            device_id=d,
            install_at=DEFAULT_TS,
            attributed_source="tiny",
            attributed_campaign="",
            attribution_event_id="C-x",
            attribution_lag_seconds=300,
        )
        for d in devices
    ]
    assert find_install_spam(events, attrs, min_installs=10) == []


def test_install_spam_purchase_counts_as_active():
    """A PURCHASE within 24h saves the device from being counted as inactive."""
    devices = [f"DP-{i}" for i in range(8)]
    events = [install_event(d, DEFAULT_TS) for d in devices]
    # Two of eight devices buy -> 25% D1, above 5% threshold.
    events.extend(purchase_event(d, DEFAULT_TS + timedelta(hours=10), 100_000) for d in devices[:2])
    attrs = [
        Attribution(
            device_id=d,
            install_at=DEFAULT_TS,
            attributed_source="ok_net",
            attributed_campaign="",
            attribution_event_id="C-x",
            attribution_lag_seconds=300,
        )
        for d in devices
    ]
    assert find_install_spam(events, attrs, min_installs=5, min_d1_rate_pct=5) == []


def test_install_spam_post_d1_open_does_not_count():
    """An OPEN > 24h after install doesn't count toward D1."""
    devices = [f"DL-{i}" for i in range(10)]
    events = [install_event(d, DEFAULT_TS) for d in devices]
    # Everyone opens at +2 days — past the D1 window.
    events.extend(open_event(d, DEFAULT_TS + timedelta(days=2)) for d in devices)
    attrs = [
        Attribution(
            device_id=d,
            install_at=DEFAULT_TS,
            attributed_source="lurker",
            attributed_campaign="",
            attribution_event_id="C-x",
            attribution_lag_seconds=300,
        )
        for d in devices
    ]
    findings = find_install_spam(events, attrs, min_installs=5)
    assert len(findings) == 1


def test_install_spam_rejects_invalid_args():
    with pytest.raises(ValueError, match="min_installs"):
        find_install_spam([], [], min_installs=0)
    with pytest.raises(ValueError, match="min_d1_rate_pct"):
        find_install_spam([], [], min_d1_rate_pct=101)


def test_install_spam_organic_source_aggregated():
    """Organic devices are judged like any other source."""
    devices = [f"DO-{i}" for i in range(10)]
    events = [install_event(d, DEFAULT_TS) for d in devices]
    attrs = [
        Attribution(
            device_id=d,
            install_at=DEFAULT_TS,
            attributed_source="organic",
            attributed_campaign="",
            attribution_event_id=None,
            attribution_lag_seconds=0,
        )
        for d in devices
    ]
    # No follow-up activity -> 0% D1 -> flagged.
    findings = find_install_spam(events, attrs, min_installs=5)
    assert len(findings) == 1
    assert findings[0].source == "organic"
