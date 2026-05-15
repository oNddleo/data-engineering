"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from clvseg.clv import CLVForecast
from clvseg.io_jsonl import (
    clv_from_dict,
    customer_from_dict,
    dump_clvs,
    dump_customers,
    dump_orders,
    dump_scores,
    load_clvs,
    load_customers,
    load_orders,
    load_scores,
    order_from_dict,
    score_from_dict,
)
from clvseg.schema import Segment

from ._fixtures import make_customer, make_order, make_score


def test_customer_roundtrip():
    c = make_customer()
    [back] = list(load_customers(dump_customers([c])))
    assert back == c


def test_order_roundtrip():
    o = make_order()
    [back] = list(load_orders(dump_orders([o])))
    assert back == o


def test_score_roundtrip():
    s = make_score()
    [back] = list(load_scores(dump_scores([s])))
    assert back == s


def test_clv_roundtrip():
    f = CLVForecast(
        customer_id="C-1",
        segment=Segment.CHAMPIONS,
        historical_aov_vnd=200_000,
        historical_frequency=5,
        window_days=180,
        expected_lifetime_days=1095,
        forecast_vnd=600_000,
    )
    [back] = list(load_clvs(dump_clvs([f])))
    assert back == f


def test_customer_decoder_rejects_bool_for_str():
    bad = {"customer_id": True, "registered_at": "2026-05-14T09:00:00+07:00", "city_key": "HCMC"}
    with pytest.raises(TypeError):
        customer_from_dict(bad)


def test_order_decoder_rejects_bool_for_int():
    bad = {
        "order_id": "O",
        "customer_id": "C",
        "gross_vnd": True,
        "n_items": 1,
        "placed_at": "2026-05-14T09:00:00+07:00",
    }
    with pytest.raises(TypeError, match="gross_vnd"):
        order_from_dict(bad)


def test_score_decoder_rejects_missing_field():
    with pytest.raises(KeyError):
        score_from_dict({"customer_id": "C"})


def test_clv_decoder_rejects_unknown_segment():
    bad = {
        "customer_id": "C",
        "segment": "FAKE_SEGMENT",
        "historical_aov_vnd": 0,
        "historical_frequency": 0,
        "window_days": 180,
        "expected_lifetime_days": 0,
        "forecast_vnd": 0,
    }
    with pytest.raises(ValueError):
        clv_from_dict(bad)


def test_blank_lines_skipped():
    text = dump_customers([make_customer()])
    padded = "\n\n" + text + "\n\n"
    assert len(list(load_customers(padded))) == 1


def test_multi_record_roundtrip():
    customers = [make_customer(customer_id=f"C-{i:03d}") for i in range(5)]
    assert list(load_customers(dump_customers(customers))) == customers
