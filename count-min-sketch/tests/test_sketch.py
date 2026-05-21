"""Unit tests for Count-Min Sketch."""

from __future__ import annotations

import pytest

from cmsketch.sketch import CountMinSketch


class TestBasic:
    def test_n_tracks_updates(self) -> None:
        s = CountMinSketch()
        for i in range(100):
            s.update(str(i))
        assert s.n == 100

    def test_update_with_count(self) -> None:
        s = CountMinSketch()
        s.update("x", count=50)
        assert s.n == 50
        assert s.query("x") >= 50

    def test_invalid_count_raises(self) -> None:
        s = CountMinSketch()
        with pytest.raises(ValueError):
            s.update("x", count=0)

    def test_invalid_width_raises(self) -> None:
        with pytest.raises(ValueError):
            CountMinSketch(width=1)

    def test_invalid_depth_raises(self) -> None:
        with pytest.raises(ValueError):
            CountMinSketch(depth=0)

    def test_zero_count_unseen_item(self) -> None:
        s = CountMinSketch()
        s.update("a")
        # Unseen item — minimum could be 0 or collide
        # At minimum the estimate for a known item >= true count
        assert s.query("a") >= 1

    def test_estimate_at_least_true_count(self) -> None:
        s = CountMinSketch(width=256, depth=4)
        true: dict[str, int] = {}
        for i in range(500):
            item = f"item_{i % 50}"
            s.update(item)
            true[item] = true.get(item, 0) + 1
        for item, cnt in true.items():
            assert s.query(item) >= cnt

    def test_type_string(self) -> None:
        s = CountMinSketch()
        s.update("hello")
        assert s.query("hello") >= 1

    def test_type_bytes(self) -> None:
        s = CountMinSketch()
        s.update(b"\x00\x01")
        assert s.query(b"\x00\x01") >= 1

    def test_type_int(self) -> None:
        s = CountMinSketch()
        s.update(42)
        assert s.query(42) >= 1

    def test_type_float(self) -> None:
        s = CountMinSketch()
        s.update(3.14)
        assert s.query(3.14) >= 1

    def test_size(self) -> None:
        s = CountMinSketch(width=100, depth=4)
        assert s.size() == 400


class TestErrorGuarantee:
    """CMS guarantee: estimate <= true + ε*N with probability >= 1-δ."""

    def test_estimate_never_below_true(self) -> None:
        s = CountMinSketch(width=512, depth=5, seed=0)
        true: dict[str, int] = {}
        for i in range(10_000):
            item = f"key_{i % 200}"
            s.update(item)
            true[item] = true.get(item, 0) + 1
        for item, cnt in true.items():
            assert s.query(item) >= cnt

    def test_overcount_bounded(self) -> None:
        """Expected overcount per item <= ε*N = (e/width)*N."""
        width = 1024
        s = CountMinSketch(width=width, depth=7, seed=1)
        true: dict[str, int] = {}
        n_updates = 20_000
        for i in range(n_updates):
            item = f"key_{i % 500}"
            s.update(item)
            true[item] = true.get(item, 0) + 1
        import math

        epsilon = math.e / width
        error_bound = epsilon * n_updates
        violations = 0
        for item, cnt in true.items():
            overcount = s.query(item) - cnt
            if overcount > error_bound:
                violations += 1
        # With δ = e^(-7) ≈ 0.0009, expect very few violations
        assert violations <= len(true) * 0.01  # at most 1% items violate

    def test_from_error_params(self) -> None:
        s = CountMinSketch.from_error_params(epsilon=0.01, delta=0.001)
        assert s.width >= 2
        assert s.depth >= 1
        # Feed some items
        for i in range(1000):
            s.update(f"item_{i % 100}")
        assert s.n == 1000

    def test_invalid_epsilon_raises(self) -> None:
        with pytest.raises(ValueError):
            CountMinSketch.from_error_params(epsilon=0.0, delta=0.01)

    def test_invalid_delta_raises(self) -> None:
        with pytest.raises(ValueError):
            CountMinSketch.from_error_params(epsilon=0.01, delta=1.5)


class TestMerge:
    def test_merge_n(self) -> None:
        s1 = CountMinSketch(width=256, depth=4, seed=5)
        s2 = CountMinSketch(width=256, depth=4, seed=5)
        for i in range(100):
            s1.update(f"a_{i}")
        for i in range(200):
            s2.update(f"b_{i}")
        merged = s1.merge(s2)
        assert merged.n == 300

    def test_merge_preserves_counts(self) -> None:
        s1 = CountMinSketch(width=512, depth=5, seed=0)
        s2 = CountMinSketch(width=512, depth=5, seed=0)
        s1.update("x", count=10)
        s2.update("x", count=20)
        merged = s1.merge(s2)
        assert merged.query("x") >= 30

    def test_merge_incompatible_raises(self) -> None:
        s1 = CountMinSketch(width=256, depth=4, seed=0)
        s2 = CountMinSketch(width=512, depth=4, seed=0)
        with pytest.raises(ValueError):
            s1.merge(s2)

    def test_merge_seed_mismatch_raises(self) -> None:
        s1 = CountMinSketch(width=256, depth=4, seed=0)
        s2 = CountMinSketch(width=256, depth=4, seed=1)
        with pytest.raises(ValueError):
            s1.merge(s2)


class TestHeavyHitters:
    def test_heavy_hitter_detected(self) -> None:
        s = CountMinSketch(width=1024, depth=5, seed=42)
        for _ in range(900):
            s.update("elephant")
        for i in range(100):
            s.update(f"other_{i}")
        candidates = ["elephant"] + [f"other_{i}" for i in range(100)]
        hh = s.heavy_hitters(candidates, threshold_fraction=0.8)
        items = [item for item, _ in hh]
        assert "elephant" in items

    def test_heavy_hitters_sorted_desc(self) -> None:
        s = CountMinSketch(width=512, depth=4, seed=0)
        s.update("a", count=100)
        s.update("b", count=50)
        s.update("c", count=10)
        hh = s.heavy_hitters(["a", "b", "c"], threshold_fraction=0.0)
        counts = [cnt for _, cnt in hh]
        assert counts == sorted(counts, reverse=True)
