"""JSONL codec tests."""

from __future__ import annotations

from flashpipe.detectors import HotnessEvent, HotnessKind
from flashpipe.io_jsonl import (
    aggregate_to_dict,
    dump_aggregates,
    dump_events,
    dump_hotness,
    event_from_dict,
    event_to_dict,
    hotness_from_dict,
    hotness_to_dict,
    load_events,
)
from flashpipe.windows import WindowAggregate

from ._fixtures import make_event, t_at


def test_event_round_trip():
    e = make_event()
    assert event_from_dict(event_to_dict(e)) == e


def test_dump_load_events():
    events = [make_event(event_id=f"E-{i}", created_at=t_at(i)) for i in range(5)]
    loaded = list(load_events(dump_events(events)))
    assert loaded == events


def test_aggregate_to_dict_serialises():
    a = WindowAggregate(
        window_start=t_at(0),
        window_end=t_at(1),
        item_id=1,
        n_views=10,
        n_add_to_cart=2,
        n_checkout=1,
        n_orders=0,
        units_sold=0,
        gmv_vnd=0,
        unique_users=5,
    )
    d = aggregate_to_dict(a)
    assert d["item_id"] == 1
    assert d["n_views"] == 10


def test_hotness_round_trip():
    h = HotnessEvent(
        kind=HotnessKind.HOT_PRODUCT,
        item_id=42,
        window_start=t_at(0),
        window_end=t_at(1),
        detail="hot!",
        metric=1234,
    )
    assert hotness_from_dict(hotness_to_dict(h)) == h


def test_dump_aggregates_jsonl_lines():
    aggs = [
        WindowAggregate(
            window_start=t_at(i),
            window_end=t_at(i + 1),
            item_id=1,
            n_views=i,
            n_add_to_cart=0,
            n_checkout=0,
            n_orders=0,
            units_sold=0,
            gmv_vnd=0,
            unique_users=0,
        )
        for i in range(3)
    ]
    out = dump_aggregates(aggs)
    assert out.count("\n") == 3


def test_dump_hotness_jsonl_lines():
    hs = [
        HotnessEvent(
            kind=HotnessKind.HOT_PRODUCT,
            item_id=i,
            window_start=t_at(0),
            window_end=t_at(1),
            detail="x",
            metric=i,
        )
        for i in range(3)
    ]
    assert dump_hotness(hs).count("\n") == 3


def test_load_events_skips_blank_lines():
    text = "\n\n" + dump_events([make_event()])
    assert len(list(load_events(text))) == 1
