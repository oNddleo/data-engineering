"""JSONL codec round-trips for every Bloom variant."""

from __future__ import annotations

import pytest

from bloom.counting import add_counting, build_counting, contains_counting
from bloom.filter import add, build, contains, freeze
from bloom.io_jsonl import (
    buildable_from_dict,
    buildable_to_dict,
    counting_from_dict,
    counting_to_dict,
    dump_filters,
    filter_from_dict,
    filter_to_dict,
    load_filters,
    scalable_from_dict,
    scalable_to_dict,
)
from bloom.scalable import add_scalable, build_scalable, contains_scalable


def test_filter_round_trip() -> None:
    bf = build(capacity=100, target_fpr=0.01)
    for i in range(50):
        add(bf, f"v-{i}")
    snap = freeze(bf)
    out = filter_from_dict(filter_to_dict(snap))
    assert out == snap


def test_filter_dump_load() -> None:
    snaps = [
        freeze(build(50, 0.01)),
        freeze(build(100, 0.01)),
    ]
    out = load_filters(dump_filters(snaps))
    assert out == snaps


def test_filter_preserves_membership_across_serialization() -> None:
    bf = build(capacity=100, target_fpr=0.01)
    for i in range(50):
        add(bf, f"v-{i}")
    snap = freeze(bf)
    text = dump_filters([snap])
    [restored] = load_filters(text)
    for i in range(50):
        assert contains(restored, f"v-{i}") is True


def test_buildable_round_trip() -> None:
    bf = build(capacity=100, target_fpr=0.01)
    for i in range(30):
        add(bf, f"v-{i}")
    out = buildable_from_dict(buildable_to_dict(bf))
    # Equal n_items + identical bit content.
    assert out.size_bits == bf.size_bits
    assert out.n_hashes == bf.n_hashes
    assert out.n_items == bf.n_items
    assert bytes(out._bits) == bytes(bf._bits)


def test_counting_round_trip() -> None:
    cb = build_counting(capacity=100, target_fpr=0.01)
    for i in range(20):
        add_counting(cb, f"v-{i}")
    out = counting_from_dict(counting_to_dict(cb))
    for i in range(20):
        assert contains_counting(out, f"v-{i}") is True


def test_scalable_round_trip() -> None:
    sb = build_scalable(initial_capacity=10, target_fpr=0.01)
    for i in range(100):
        add_scalable(sb, f"v-{i}")
    out = scalable_from_dict(scalable_to_dict(sb))
    assert out.n_slices == sb.n_slices
    for i in range(100):
        assert contains_scalable(out, f"v-{i}") is True


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_filters("[1, 2, 3]\n")


def test_load_skips_blank_lines() -> None:
    snap = freeze(build(50, 0.01))
    text = "\n\n" + dump_filters([snap]) + "\n\n"
    out = load_filters(text)
    assert out == [snap]
