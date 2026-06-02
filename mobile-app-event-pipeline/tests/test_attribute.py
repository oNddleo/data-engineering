"""Last-touch attribution behaviour."""

from __future__ import annotations

from datetime import timedelta

import pytest

from mappev.attribute import attribute

from ._fixtures import (
    DEFAULT_TS,
    click_event,
    impression_event,
    install_event,
)


def test_organic_install_no_touchpoints():
    """An install with no preceding click/impression is organic."""
    events = [install_event("D-1", DEFAULT_TS)]
    [a] = attribute(events)
    assert a.attributed_source == "organic"
    assert a.attribution_event_id is None
    assert a.attribution_lag_seconds == 0


def test_click_attribution_inside_window():
    """A click 3 days before install attributes the install."""
    install_at = DEFAULT_TS
    click_at = install_at - timedelta(days=3)
    events = [
        click_event("D-1", click_at, source="facebook", campaign="vn_promo"),
        install_event("D-1", install_at),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "facebook"
    assert a.attributed_campaign == "vn_promo"
    assert a.attribution_lag_seconds == int(timedelta(days=3).total_seconds())


def test_click_attribution_outside_window_is_organic():
    """A click 10 days before install — outside the 7d window — is ignored."""
    install_at = DEFAULT_TS
    click_at = install_at - timedelta(days=10)
    events = [
        click_event("D-1", click_at),
        install_event("D-1", install_at),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "organic"


def test_click_attribution_uses_last_qualifying():
    """Of multiple qualifying clicks, the most recent wins."""
    install_at = DEFAULT_TS
    events = [
        click_event("D-1", install_at - timedelta(days=5), source="google_ads", campaign="search"),
        click_event("D-1", install_at - timedelta(days=1), source="facebook", campaign="vn_promo"),
        install_event("D-1", install_at),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "facebook"


def test_view_attribution_when_no_click():
    """An impression 12h before install attributes when no click qualifies."""
    install_at = DEFAULT_TS
    impr_at = install_at - timedelta(hours=12)
    events = [
        impression_event("D-1", impr_at, source="tiktok", campaign="vn_videoview"),
        install_event("D-1", install_at),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "tiktok"


def test_click_overrides_view():
    """If both a click and an impression qualify, click wins."""
    install_at = DEFAULT_TS
    events = [
        click_event("D-1", install_at - timedelta(days=1), source="google_ads", campaign="uac"),
        impression_event(
            "D-1", install_at - timedelta(hours=2), source="tiktok", campaign="vn_videoview"
        ),
        install_event("D-1", install_at),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "google_ads"


def test_view_outside_window_is_organic():
    """An impression > 24h before install is outside the view window."""
    install_at = DEFAULT_TS
    events = [
        impression_event("D-1", install_at - timedelta(hours=30)),
        install_event("D-1", install_at),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "organic"


def test_click_after_install_is_ignored():
    """A click AFTER the install doesn't attribute — only before."""
    install_at = DEFAULT_TS
    events = [
        install_event("D-1", install_at),
        click_event("D-1", install_at + timedelta(hours=1)),
    ]
    [a] = attribute(events)
    assert a.attributed_source == "organic"


def test_attribute_skips_clicks_from_other_devices():
    """A click on device A doesn't attribute device B's install."""
    install_at = DEFAULT_TS
    events = [
        click_event("D-A", install_at - timedelta(days=1)),
        install_event("D-B", install_at),
    ]
    [a] = attribute(events)
    assert a.device_id == "D-B"
    assert a.attributed_source == "organic"


def test_attribute_validates_windows():
    with pytest.raises(ValueError):
        attribute([], click_window=timedelta(0))
    with pytest.raises(ValueError):
        attribute([], view_window=timedelta(0))


def test_output_sorted_by_install_then_device():
    """Multiple installs sorted by (install_at, device_id)."""
    events = [
        install_event("D-2", DEFAULT_TS + timedelta(hours=2)),
        install_event("D-1", DEFAULT_TS),
        install_event("D-3", DEFAULT_TS + timedelta(hours=1)),
    ]
    out = attribute(events)
    ids = [a.device_id for a in out]
    assert ids == ["D-1", "D-3", "D-2"]


def test_custom_click_window():
    """Caller can override the default 7-day click window."""
    install_at = DEFAULT_TS
    events = [
        click_event("D-1", install_at - timedelta(hours=12)),
        install_event("D-1", install_at),
    ]
    # 1h window → click outside the window, organic.
    [a] = attribute(events, click_window=timedelta(hours=1))
    assert a.attributed_source == "organic"
