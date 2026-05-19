"""Scan-skipping + abnormal-dwell detection."""

from __future__ import annotations

from datetime import timedelta

import pytest

from vnpost.fraud import FraudKind, find_abnormal_dwell, find_scan_skipping
from vnpost.state import stitch

from ._fixtures import (
    DEFAULT_TS,
    at_hub,
    delivered,
    in_transit,
    out_for_delivery,
    picked_up,
)


def test_scan_skipping_inter_city_flagged():
    """3-event inter-city delivery → scan-skipping."""
    events = [
        picked_up("T-1", DEFAULT_TS, hub="HCM-TPN"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=4), "HN-CG"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=6)),
    ]
    parcels = stitch(events)
    findings = find_scan_skipping(parcels)
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.SCAN_SKIPPING
    assert findings[0].tracking_id == "T-1"


def test_scan_skipping_same_city_not_flagged():
    """3-event same-city delivery is legitimate."""
    events = [
        picked_up("T-1", DEFAULT_TS, hub="HCM-TPN"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=4), "HCM-Q12"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=6)),
    ]
    parcels = stitch(events)
    assert find_scan_skipping(parcels) == []


def test_scan_skipping_full_journey_not_flagged():
    """A normally-scanned inter-city parcel doesn't get flagged."""
    events = [
        picked_up("T-1", DEFAULT_TS, hub="HCM-TPN"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=2), "HCM-TPN"),
        in_transit("T-1", DEFAULT_TS + timedelta(hours=8), "VN-NSC"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=18), "HN-CG"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=22), "HN-CG"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=24)),
    ]
    parcels = stitch(events)
    assert find_scan_skipping(parcels) == []


def test_scan_skipping_undelivered_not_flagged():
    """Returned or pending parcels can have any event count."""
    events = [
        picked_up("T-1", DEFAULT_TS, hub="HCM-TPN"),
    ]
    parcels = stitch(events)
    assert find_scan_skipping(parcels) == []


def test_scan_skipping_rejects_invalid_threshold():
    with pytest.raises(ValueError, match="thresholds must be >= 2"):
        find_scan_skipping([], min_events_inter_city=1)


# ---------- abnormal dwell ---------------------------------------------------


def test_abnormal_dwell_detects_outlier():
    """Build a population with mostly short dwells + 1 long outlier."""
    events = []
    # 19 parcels with normal dwell (10-12h between hub events).
    for i in range(19):
        events.extend(
            [
                picked_up(f"T-N-{i:03d}", DEFAULT_TS + timedelta(days=i), hub="HCM-TPN"),
                at_hub(f"T-N-{i:03d}", DEFAULT_TS + timedelta(days=i, hours=2), "HCM-TPN"),
                in_transit(f"T-N-{i:03d}", DEFAULT_TS + timedelta(days=i, hours=14), "VN-NSC"),
                at_hub(f"T-N-{i:03d}", DEFAULT_TS + timedelta(days=i, hours=26), "HN-CG"),
                out_for_delivery(f"T-N-{i:03d}", DEFAULT_TS + timedelta(days=i, hours=28), "HN-CG"),
                delivered(f"T-N-{i:03d}", DEFAULT_TS + timedelta(days=i, hours=30)),
            ]
        )
    # 1 outlier: stuck at VN-NSC for 200 hours.
    base = DEFAULT_TS + timedelta(days=20)
    events.extend(
        [
            picked_up("T-OUT", base, hub="HCM-TPN"),
            at_hub("T-OUT", base + timedelta(hours=2), "HCM-TPN"),
            in_transit("T-OUT", base + timedelta(hours=10), "VN-NSC"),
            at_hub("T-OUT", base + timedelta(hours=210), "HN-CG"),
            out_for_delivery("T-OUT", base + timedelta(hours=212), "HN-CG"),
            delivered("T-OUT", base + timedelta(hours=214)),
        ]
    )
    findings = find_abnormal_dwell(events)
    assert any(f.tracking_id == "T-OUT" for f in findings)


def test_abnormal_dwell_empty_returns_empty():
    assert find_abnormal_dwell([]) == []


def test_abnormal_dwell_rejects_zero_multiplier():
    with pytest.raises(ValueError, match="iqr_multiplier"):
        find_abnormal_dwell([], iqr_multiplier=0)


def test_abnormal_dwell_no_outliers_returns_empty():
    """Uniform-dwell population produces no findings."""
    events = []
    for i in range(10):
        events.extend(
            [
                picked_up(f"T-{i}", DEFAULT_TS + timedelta(days=i), hub="HCM-TPN"),
                at_hub(f"T-{i}", DEFAULT_TS + timedelta(days=i, hours=10), "HN-CG"),
                delivered(f"T-{i}", DEFAULT_TS + timedelta(days=i, hours=12)),
            ]
        )
    findings = find_abnormal_dwell(events)
    # All dwells around 10h — none > p95 + 3 * (p95 - p50)
    assert findings == []
