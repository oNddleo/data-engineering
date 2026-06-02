"""JSONL codec round-trips for every record type."""

from __future__ import annotations

from datetime import timedelta

import pytest

from mappev.fraud import FraudFinding, FraudKind
from mappev.io_jsonl import (
    attribution_from_dict,
    attribution_to_dict,
    dump_attributions,
    dump_events,
    dump_frauds,
    dump_ltvs,
    dump_retentions,
    event_from_dict,
    event_to_dict,
    fraud_from_dict,
    fraud_to_dict,
    load_attributions,
    load_events,
    load_frauds,
    load_ltvs,
    load_retentions,
    ltv_from_dict,
    ltv_to_dict,
    retention_from_dict,
    retention_to_dict,
)
from mappev.schema import (
    Attribution,
    CohortLTV,
    CohortRetention,
    EventKind,
)

from ._fixtures import (
    DEFAULT_TS,
    click_event,
    install_event,
    make_event,
    purchase_event,
)


def test_event_dict_round_trip_install():
    e = install_event("D-1", DEFAULT_TS)
    out = event_from_dict(event_to_dict(e))
    assert out == e


def test_event_dict_round_trip_click():
    e = click_event("D-1", DEFAULT_TS + timedelta(hours=3), source="zalo", campaign="vn_brand")
    out = event_from_dict(event_to_dict(e))
    assert out.source == "zalo"
    assert out.campaign == "vn_brand"
    assert out.kind is EventKind.CLICK


def test_event_dict_round_trip_in_app():
    e = make_event(
        event_id="E-IA-1",
        kind=EventKind.IN_APP,
        in_app_event_name="level_up",
    )
    out = event_from_dict(event_to_dict(e))
    assert out.in_app_event_name == "level_up"
    assert out.kind is EventKind.IN_APP


def test_event_dict_round_trip_purchase():
    e = purchase_event("D-1", DEFAULT_TS, 250_000)
    out = event_from_dict(event_to_dict(e))
    assert out.revenue_vnd == 250_000
    assert out.kind is EventKind.PURCHASE


def test_event_round_trip_via_dump_load_many():
    events = [install_event(f"D-{i}", DEFAULT_TS + timedelta(hours=i)) for i in range(10)]
    text = dump_events(events)
    loaded = load_events(text)
    assert loaded == events


def test_event_dump_emits_newline_terminated_lines():
    events = [install_event("D-1", DEFAULT_TS)]
    text = dump_events(events)
    assert text.endswith("\n")
    assert text.count("\n") == 1


def test_event_load_skips_blank_lines():
    e = install_event("D-1", DEFAULT_TS)
    raw = dump_events([e]) + "\n\n   \n"
    [out] = load_events(raw)
    assert out == e


def test_event_load_rejects_non_object_line():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_events("[1, 2, 3]\n")


def test_event_load_rejects_bool_revenue():
    """A bool sneaking in as int must be rejected."""
    text = (
        '{"event_id":"E1","device_id":"D1","kind":"PURCHASE",'
        '"occurred_at":"2026-05-17T09:00:00+07:00","source":"organic",'
        '"campaign":"","revenue_vnd":true,"in_app_event_name":""}\n'
    )
    with pytest.raises(TypeError, match="revenue_vnd must be int"):
        load_events(text)


def test_attribution_dict_round_trip():
    a = Attribution(
        device_id="D-1",
        install_at=DEFAULT_TS,
        attributed_source="facebook",
        attributed_campaign="vn_brand",
        attribution_event_id="C-1",
        attribution_lag_seconds=1234,
    )
    assert attribution_from_dict(attribution_to_dict(a)) == a


def test_attribution_organic_round_trip():
    """attribution_event_id=None must round-trip."""
    a = Attribution(
        device_id="D-2",
        install_at=DEFAULT_TS,
        attributed_source="organic",
        attributed_campaign="",
        attribution_event_id=None,
        attribution_lag_seconds=0,
    )
    out = attribution_from_dict(attribution_to_dict(a))
    assert out.attribution_event_id is None


def test_attribution_dump_load_round_trip():
    items = [
        Attribution(
            device_id=f"D-{i}",
            install_at=DEFAULT_TS,
            attributed_source="google_ads",
            attributed_campaign="vn",
            attribution_event_id=f"C-{i}",
            attribution_lag_seconds=i * 60,
        )
        for i in range(5)
    ]
    assert load_attributions(dump_attributions(items)) == items


def test_retention_round_trip():
    r = CohortRetention(
        cohort_date="2026-05-17",
        cohort_size=42,
        d1_active=20,
        d7_active=10,
        d30_active=3,
    )
    assert retention_from_dict(retention_to_dict(r)) == r
    assert load_retentions(dump_retentions([r])) == [r]


def test_ltv_round_trip():
    c = CohortLTV(
        cohort_date="2026-05-17",
        cohort_size=10,
        revenue_d1_vnd=1_000_000,
        revenue_d7_vnd=5_000_000,
        revenue_d30_vnd=20_000_000,
    )
    assert ltv_from_dict(ltv_to_dict(c)) == c
    assert load_ltvs(dump_ltvs([c])) == [c]


def test_fraud_round_trip():
    f = FraudFinding(
        kind=FraudKind.CLICK_INJECTION,
        source="dodgy:shady",
        detail="42 installs with lag < 20s",
        metric=42,
        devices_affected=42,
    )
    assert fraud_from_dict(fraud_to_dict(f)) == f
    assert load_frauds(dump_frauds([f])) == [f]


def test_event_from_dict_rejects_str_revenue():
    bad = {
        "event_id": "E1",
        "device_id": "D1",
        "kind": "INSTALL",
        "occurred_at": DEFAULT_TS.isoformat(),
        "source": "organic",
        "campaign": "",
        "revenue_vnd": "1000",
        "in_app_event_name": "",
    }
    with pytest.raises(TypeError, match="revenue_vnd must be int"):
        event_from_dict(bad)


def test_attribution_from_dict_rejects_non_str_event_id():
    bad = {
        "device_id": "D-1",
        "install_at": DEFAULT_TS.isoformat(),
        "attributed_source": "facebook",
        "attributed_campaign": "vn",
        "attribution_event_id": 123,  # must be str | null
        "attribution_lag_seconds": 100,
    }
    with pytest.raises(TypeError, match="attribution_event_id"):
        attribution_from_dict(bad)
