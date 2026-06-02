"""Schema invariants."""

from __future__ import annotations

from datetime import datetime

import pytest

from multiprice.schema import VN_TZ, Platform

from ._fixtures import make_mapping, make_obs


def test_platform_enum():
    assert {p.value for p in Platform} == {"SHOPEE", "LAZADA", "TIKI"}


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_mapping_happy_path():
    m = make_mapping()
    assert m.canonical_sku == "SKU-1"


def test_mapping_rejects_empty_sku():
    with pytest.raises(ValueError):
        make_mapping(canonical_sku="")


def test_mapping_rejects_empty_item_id():
    with pytest.raises(ValueError):
        make_mapping(platform_item_id="")


def test_obs_happy_path():
    o = make_obs(price=100_000, stock=10)
    assert o.is_in_stock


def test_obs_out_of_stock():
    o = make_obs(stock=0)
    assert not o.is_in_stock


def test_obs_rejects_non_positive_price():
    with pytest.raises(ValueError):
        make_obs(price=0)


def test_obs_rejects_price_above_original():
    with pytest.raises(ValueError):
        make_obs(price=200_000, original_price=100_000)


def test_obs_rejects_negative_stock():
    with pytest.raises(ValueError):
        make_obs(stock=-1)


def test_obs_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_obs(observed_at=datetime(2026, 5, 14, 9, 0))


def test_obs_rejects_empty_sku():
    with pytest.raises(ValueError):
        make_obs(canonical_sku="")


def test_obs_rejects_blank_name():
    with pytest.raises(ValueError):
        make_obs(name="  ")
