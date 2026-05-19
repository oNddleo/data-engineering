"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from tdigest.digest import add, build, freeze, quantile
from tdigest.io_jsonl import (
    digest_from_dict,
    digest_to_dict,
    dump_digests,
    load_digests,
)


def test_digest_roundtrip() -> None:
    td = build(compression=100.0)
    for v in range(100):
        add(td, float(v))
    snap = freeze(td)
    out = digest_from_dict(digest_to_dict(snap))
    assert out == snap


def test_dump_load_multiple() -> None:
    snaps = []
    for i in range(3):
        td = build(compression=100.0)
        for v in range(50):
            add(td, float(v + i * 100))
        snaps.append(freeze(td))
    out = load_digests(dump_digests(snaps))
    assert out == snaps


def test_preserved_quantile_after_roundtrip() -> None:
    """Query results before and after round-trip must match."""
    td = build(compression=100.0)
    for v in range(1000):
        add(td, float(v))
    snap = freeze(td)
    restored = load_digests(dump_digests([snap]))[0]
    for q in (0.1, 0.5, 0.9, 0.99):
        assert quantile(snap, q) == quantile(restored, q)


def test_dump_skips_blank_lines() -> None:
    td = build(compression=100.0)
    add(td, 1.0)
    snap = freeze(td)
    text = "\n\n" + dump_digests([snap]) + "\n\n"
    assert load_digests(text) == [snap]


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_digests("[1, 2, 3]\n")


def test_load_rejects_bad_centroid_format() -> None:
    """Centroid must be [mean, weight], not a scalar."""
    bad = (
        '{"compression": 100.0, "centroids": [42], '
        '"total_weight": 1.0, "min_value": 0.0, "max_value": 1.0}\n'
    )
    with pytest.raises(TypeError, match="centroid"):
        load_digests(bad)
