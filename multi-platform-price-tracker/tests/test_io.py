"""JSONL codec tests."""

from __future__ import annotations

from multiprice.io_jsonl import (
    dump_mappings,
    dump_observations,
    load_mappings,
    load_observations,
    mapping_from_dict,
    mapping_to_dict,
    obs_from_dict,
    obs_to_dict,
)

from ._fixtures import make_mapping, make_obs, t_at


def test_mapping_round_trip():
    m = make_mapping()
    assert mapping_from_dict(mapping_to_dict(m)) == m


def test_obs_round_trip():
    o = make_obs(price=200_000, original_price=250_000, observed_at=t_at(60))
    assert obs_from_dict(obs_to_dict(o)) == o


def test_dump_load_mappings():
    ms = [make_mapping(canonical_sku=f"SKU-{i}", platform_item_id=f"sp-{i}") for i in range(5)]
    loaded = list(load_mappings(dump_mappings(ms)))
    assert loaded == ms


def test_dump_load_observations():
    obs = [make_obs(canonical_sku=f"S-{i}", observed_at=t_at(i * 10)) for i in range(5)]
    loaded = list(load_observations(dump_observations(obs)))
    assert loaded == obs


def test_load_skips_blank_lines():
    text = "\n\n" + dump_mappings([make_mapping()])
    assert len(list(load_mappings(text))) == 1
