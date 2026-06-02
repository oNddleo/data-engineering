"""Unit tests for HyperLogLog sketch."""

from __future__ import annotations

import pytest

from hllsketch.sketch import HyperLogLog, _rho


class TestRho:
    def test_zero_bits_returns_max_plus_one(self) -> None:
        assert _rho(0, 10) == 11

    def test_msb_set_returns_one(self) -> None:
        # 1000...0 in 10 bits → leading zeros = 0 → rho = 1
        assert _rho(1 << 9, 10) == 1

    def test_all_leading_zeros_then_one(self) -> None:
        # 0000000001 in 10 bits → 9 leading zeros → rho = 10
        assert _rho(1, 10) == 10


class TestBasic:
    def test_empty_count_is_zero_ish(self) -> None:
        h = HyperLogLog(precision=10)
        # empty sketch should estimate near 0
        assert h.count() == 0

    def test_invalid_precision_low_raises(self) -> None:
        with pytest.raises(ValueError):
            HyperLogLog(precision=3)

    def test_invalid_precision_high_raises(self) -> None:
        with pytest.raises(ValueError):
            HyperLogLog(precision=19)

    def test_num_registers(self) -> None:
        h = HyperLogLog(precision=10)
        assert h.num_registers == 1024

    def test_size_bytes(self) -> None:
        h = HyperLogLog(precision=12)
        assert h.size_bytes() == 4096

    def test_add_single_item(self) -> None:
        h = HyperLogLog(precision=12)
        h.add("hello")
        assert h.count() >= 1


class TestAccuracy:
    """HLL error ~ 1.04/sqrt(m). For precision=14, m=16384, σ≈0.81%."""

    def _error_pct(self, estimated: int, true: int) -> float:
        return abs(estimated - true) / true * 100

    def test_small_cardinality(self) -> None:
        h = HyperLogLog(precision=12)
        for i in range(100):
            h.add(f"item_{i}")
        est = h.count()
        assert self._error_pct(est, 100) < 20  # generous for small n

    def test_medium_cardinality(self) -> None:
        h = HyperLogLog(precision=14)
        for i in range(10_000):
            h.add(f"user_{i}")
        est = h.count()
        # Error < 5% (theoretical σ ≈ 0.81%)
        assert self._error_pct(est, 10_000) < 5.0

    def test_large_cardinality(self) -> None:
        h = HyperLogLog(precision=14)
        for i in range(100_000):
            h.add(f"event_{i}")
        est = h.count()
        assert self._error_pct(est, 100_000) < 5.0

    def test_duplicates_do_not_inflate(self) -> None:
        h = HyperLogLog(precision=12)
        for _ in range(100):
            h.add("same_item")
        assert h.count() <= 5  # should estimate ~1

    def test_repeated_items_same_as_distinct(self) -> None:
        """Adding the same set 10x should give same estimate as once."""
        h1 = HyperLogLog(precision=12)
        h2 = HyperLogLog(precision=12)
        items = [f"x_{i}" for i in range(1000)]
        for item in items:
            h1.add(item)
        for _ in range(10):
            for item in items:
                h2.add(item)
        # Both should estimate ~1000
        assert abs(h1.count() - h2.count()) <= max(50, h1.count() // 10)

    def test_different_items_give_different_estimates(self) -> None:
        h1 = HyperLogLog(precision=12)
        h2 = HyperLogLog(precision=12)
        for i in range(1000):
            h1.add(f"a_{i}")
        for i in range(5000):
            h2.add(f"b_{i}")
        assert h2.count() > h1.count()


class TestMerge:
    def test_merge_same_precision(self) -> None:
        h1 = HyperLogLog(precision=12)
        h2 = HyperLogLog(precision=12)
        for i in range(1000):
            h1.add(f"a_{i}")
        for i in range(1000):
            h2.add(f"b_{i}")
        merged = h1.merge(h2)
        # Should estimate ~2000 distinct
        est = merged.count()
        assert 1200 <= est <= 2800

    def test_merge_disjoint_vs_union(self) -> None:
        h1 = HyperLogLog(precision=14)
        h2 = HyperLogLog(precision=14)
        for i in range(5000):
            h1.add(f"x_{i}")
        for i in range(5000):
            h2.add(f"y_{i}")
        merged = h1.merge(h2)
        est = merged.count()
        assert abs(est - 10_000) / 10_000 < 0.05

    def test_merge_incompatible_precision_raises(self) -> None:
        h1 = HyperLogLog(precision=10)
        h2 = HyperLogLog(precision=12)
        with pytest.raises(ValueError):
            h1.merge(h2)

    def test_merge_identical_is_same(self) -> None:
        h = HyperLogLog(precision=12)
        for i in range(2000):
            h.add(f"item_{i}")
        merged = h.merge(h)
        assert merged.count() == h.count()

    def test_merge_n_equals_union_cardinality(self) -> None:
        h1 = HyperLogLog(precision=12)
        h2 = HyperLogLog(precision=12)
        # Overlapping sets
        for i in range(500):
            h1.add(f"shared_{i}")
        for i in range(500):
            h1.add(f"only1_{i}")
        for i in range(500):
            h2.add(f"shared_{i}")
        for i in range(500):
            h2.add(f"only2_{i}")
        # True union = 1500 distinct
        merged = h1.merge(h2)
        est = merged.count()
        assert abs(est - 1500) / 1500 < 0.10


class TestTypes:
    def test_str_type(self) -> None:
        h = HyperLogLog()
        h.add("hello")
        assert h.count() >= 1

    def test_bytes_type(self) -> None:
        h = HyperLogLog()
        h.add(b"\x00\x01\x02")
        assert h.count() >= 1

    def test_int_type(self) -> None:
        h = HyperLogLog()
        h.add(12345)
        assert h.count() >= 1

    def test_float_type(self) -> None:
        h = HyperLogLog()
        h.add(3.14159)
        assert h.count() >= 1
