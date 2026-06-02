"""JSONL codec round-trips."""

from __future__ import annotations

import random

import pytest

from reservoir.algorithms import sample_r, sample_weighted
from reservoir.io_jsonl import (
    dump_reservoirs,
    dump_weighted,
    load_reservoirs,
    load_weighted,
    reservoir_from_dict,
    reservoir_to_dict,
    weighted_from_dict,
    weighted_to_dict,
)


def test_reservoir_roundtrip_basic() -> None:
    res = sample_r([f"v-{i}" for i in range(20)], capacity=5, rng=random.Random(0))
    out = reservoir_from_dict(reservoir_to_dict(res))
    assert out == res


def test_reservoir_dump_load_multiple() -> None:
    snaps = [
        sample_r([f"v-{i}" for i in range(50)], capacity=5, rng=random.Random(i)) for i in range(3)
    ]
    out = load_reservoirs(dump_reservoirs(snaps))
    assert out == snaps


def test_reservoir_dump_skips_blank_lines() -> None:
    snap = sample_r(["a", "b"], capacity=5)
    text = "\n\n" + dump_reservoirs([snap]) + "\n\n"
    assert load_reservoirs(text) == [snap]


def test_reservoir_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_reservoirs("[1, 2, 3]\n")


def test_reservoir_load_rejects_non_str_item() -> None:
    bad = '{"capacity": 5, "items": [123], "n_seen": 1}\n'
    with pytest.raises(TypeError, match="item"):
        load_reservoirs(bad)


# ---------- Weighted -------------------------------------------------------


def test_weighted_roundtrip() -> None:
    pairs = [(f"v-{i}", float(i + 1)) for i in range(10)]
    res = sample_weighted(pairs, capacity=5, rng=random.Random(0))
    out = weighted_from_dict(weighted_to_dict(res))
    assert out.items == res.items
    assert out.n_seen == res.n_seen
    assert out.total_weight_seen == res.total_weight_seen


def test_weighted_dump_load() -> None:
    pairs = [(f"v-{i}", float(i + 1)) for i in range(10)]
    snaps = [sample_weighted(pairs, capacity=5, rng=random.Random(i)) for i in range(2)]
    text = dump_weighted(snaps)
    restored = load_weighted(text)
    assert len(restored) == 2
    for orig, back in zip(snaps, restored, strict=True):
        assert orig.items == back.items
