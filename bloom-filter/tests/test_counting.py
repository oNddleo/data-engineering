"""CountingBloom: add, remove, contains, saturation."""

from __future__ import annotations

from bloom.counting import (
    add_counting,
    build_counting,
    contains_counting,
    remove_counting,
)


def test_counting_basic_add_contains() -> None:
    cb = build_counting(capacity=100, target_fpr=0.01)
    add_counting(cb, "alpha")
    assert contains_counting(cb, "alpha") is True
    assert contains_counting(cb, "beta") is False


def test_counting_remove_makes_absent() -> None:
    cb = build_counting(capacity=100, target_fpr=0.01)
    add_counting(cb, "alpha")
    assert remove_counting(cb, "alpha") is True
    # Note: due to hash collisions with other items, contains could be False
    # only when no collision. Single item, so no collision possible.
    assert contains_counting(cb, "alpha") is False


def test_counting_remove_unknown_returns_false() -> None:
    cb = build_counting(capacity=100, target_fpr=0.01)
    add_counting(cb, "alpha")
    assert remove_counting(cb, "beta") is False
    # alpha must still be present.
    assert contains_counting(cb, "alpha") is True


def test_counting_n_items_tracks() -> None:
    cb = build_counting(capacity=100, target_fpr=0.01)
    for i in range(10):
        add_counting(cb, f"v-{i}")
    assert cb.n_items == 10
    removed = sum(remove_counting(cb, f"v-{i}") for i in range(3))
    assert removed == 3
    assert cb.n_items == 7


def test_counting_no_false_negatives_after_partial_remove() -> None:
    """After removing some items, the remaining ones must still be found."""
    cb = build_counting(capacity=200, target_fpr=0.01)
    values = [f"v-{i}" for i in range(50)]
    for v in values:
        add_counting(cb, v)
    # Remove the first 20.
    for v in values[:20]:
        remove_counting(cb, v)
    # The remaining 30 must still be present.
    for v in values[20:]:
        assert contains_counting(cb, v) is True


def test_counting_double_add_double_remove() -> None:
    """Counters track multiplicity."""
    cb = build_counting(capacity=100, target_fpr=0.01)
    add_counting(cb, "alpha")
    add_counting(cb, "alpha")
    # First remove: still present (counter went 2→1).
    remove_counting(cb, "alpha")
    assert contains_counting(cb, "alpha") is True
    # Second remove: now absent.
    remove_counting(cb, "alpha")
    assert contains_counting(cb, "alpha") is False


def test_counting_saturation_safe() -> None:
    """Adding > 255 copies should not crash and should preserve membership."""
    cb = build_counting(capacity=100, target_fpr=0.01)
    for _ in range(300):
        add_counting(cb, "alpha")
    assert contains_counting(cb, "alpha") is True
