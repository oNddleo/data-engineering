"""ScalableBloom: dynamic growth + bounded cumulative FPR."""

from __future__ import annotations

from bloom.scalable import (
    add_scalable,
    build_scalable,
    contains_scalable,
    cumulative_fpr_bound,
)


def test_scalable_starts_with_one_slice() -> None:
    sb = build_scalable(initial_capacity=100, target_fpr=0.01)
    assert sb.n_slices == 1
    assert sb.n_items == 0


def test_scalable_no_false_negatives() -> None:
    """Every inserted value must be findable even after multiple growth events."""
    sb = build_scalable(initial_capacity=100, target_fpr=0.01)
    values = [f"v-{i}" for i in range(1_000)]
    for v in values:
        add_scalable(sb, v)
    for v in values:
        assert contains_scalable(sb, v) is True


def test_scalable_grows_when_full() -> None:
    sb = build_scalable(initial_capacity=10, target_fpr=0.01)
    for i in range(30):
        add_scalable(sb, f"v-{i}")
    # Must have spawned at least one extra slice.
    assert sb.n_slices >= 2


def test_scalable_growth_pattern() -> None:
    """Each new slice should have ~growth_factor× capacity of the previous."""
    sb = build_scalable(
        initial_capacity=10,
        target_fpr=0.1,
        growth_factor=2,
        tightening_ratio=0.5,
    )
    for i in range(200):
        add_scalable(sb, f"v-{i}")
    capacities = [s.capacity for s in sb.slices]
    for i in range(1, len(capacities)):
        assert capacities[i] == capacities[i - 1] * 2


def test_scalable_fpr_tightens_with_slices() -> None:
    sb = build_scalable(
        initial_capacity=10,
        target_fpr=0.1,
        growth_factor=2,
        tightening_ratio=0.5,
    )
    for i in range(200):
        add_scalable(sb, f"v-{i}")
    fprs = [s.target_fpr for s in sb.slices]
    # Each subsequent slice has half the FPR of the previous.
    for i in range(1, len(fprs)):
        assert fprs[i] < fprs[i - 1]


def test_scalable_cumulative_fpr_bounded() -> None:
    """Cumulative FPR ≤ p0 / (1 − r) — geometric series bound."""
    sb = build_scalable(initial_capacity=10, target_fpr=0.01)
    for i in range(500):
        add_scalable(sb, f"v-{i}")
    geometric_limit = 0.01 / (1 - 0.5)  # 0.02
    assert cumulative_fpr_bound(sb) <= geometric_limit + 1e-9


def test_scalable_n_items_sums_across_slices() -> None:
    sb = build_scalable(initial_capacity=20, target_fpr=0.01)
    for i in range(100):
        add_scalable(sb, f"v-{i}")
    assert sb.n_items == 100


def test_scalable_missing_value_is_false() -> None:
    sb = build_scalable(initial_capacity=100, target_fpr=0.01)
    for i in range(50):
        add_scalable(sb, f"v-{i}")
    # Out-of-distribution probes should mostly miss.
    misses = sum(1 for i in range(100, 200) if not contains_scalable(sb, f"v-{i}"))
    assert misses >= 95  # at most 5/100 false positives
