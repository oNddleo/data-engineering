"""Comprehensive tests for the featstore package (40+ tests)."""

from __future__ import annotations

import json
import math
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from featstore.batch import BatchProcessor, DistributionStats
from featstore.registry import DuplicateFeatureError, FeatureNotFoundError, FeatureRegistry
from featstore.skew import SkewAlert, SkewDetector, _ks_two_sample, _psi_from_histograms
from featstore.store import FeatureStore
from featstore.stream import RunningStats, StreamProcessor
from featstore.transforms import (
    BucketizeTransform,
    IdentityTransform,
    LagTransform,
    Log1pTransform,
    ZScoreTransform,
    get_transform,
)
from featstore.types import FeatureSpec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS0 = datetime(2024, 1, 1, 0, 0, 0)


def _ts(offset_seconds: int) -> datetime:
    return _TS0 + timedelta(seconds=offset_seconds)


def _spec(name: str, transform: str = "identity") -> FeatureSpec:
    return FeatureSpec(name=name, dtype="float", transform=transform, description="test")


# ---------------------------------------------------------------------------
# TestFeatureRegistry
# ---------------------------------------------------------------------------


class TestFeatureRegistry:
    def test_register_and_get(self) -> None:
        reg = FeatureRegistry()
        spec = _spec("age")
        reg.register(spec)
        assert reg.get("age") is spec

    def test_list_features_sorted(self) -> None:
        reg = FeatureRegistry()
        reg.register(_spec("z_feat"))
        reg.register(_spec("a_feat"))
        reg.register(_spec("m_feat"))
        assert reg.list_features() == ["a_feat", "m_feat", "z_feat"]

    def test_duplicate_raises(self) -> None:
        reg = FeatureRegistry()
        reg.register(_spec("dup"))
        with pytest.raises(DuplicateFeatureError):
            reg.register(_spec("dup"))

    def test_missing_raises(self) -> None:
        reg = FeatureRegistry()
        with pytest.raises(FeatureNotFoundError):
            reg.get("ghost")

    def test_len(self) -> None:
        reg = FeatureRegistry()
        assert len(reg) == 0
        reg.register(_spec("x"))
        assert len(reg) == 1

    def test_list_features_empty(self) -> None:
        reg = FeatureRegistry()
        assert reg.list_features() == []

    def test_thread_safe_concurrent_register(self) -> None:
        """Concurrent registrations of different features should not corrupt state."""
        reg = FeatureRegistry()
        errors: list[Exception] = []

        def _register(n: int) -> None:
            try:
                reg.register(_spec(f"feat_{n}"))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(reg) == 50


# ---------------------------------------------------------------------------
# TestTransforms
# ---------------------------------------------------------------------------


class TestTransforms:
    def test_identity(self) -> None:
        t = IdentityTransform()
        assert t.apply(42.0) == 42.0
        assert t.apply(0.0) == 0.0
        assert t.apply(-7.5) == -7.5
        assert t.name == "identity"

    def test_zscore_normal(self) -> None:
        t = ZScoreTransform(mean=10.0, std=2.0)
        assert t.apply(12.0) == pytest.approx(1.0)
        assert t.apply(8.0) == pytest.approx(-1.0)
        assert t.apply(10.0) == pytest.approx(0.0)

    def test_zscore_zero_std(self) -> None:
        t = ZScoreTransform(mean=5.0, std=0.0)
        assert t.apply(99.0) == 0.0
        assert t.apply(0.0) == 0.0

    def test_zscore_inverse(self) -> None:
        t = ZScoreTransform(mean=3.0, std=1.5)
        z = t.apply(6.0)
        assert t.inverse(z) == pytest.approx(6.0)

    def test_log1p(self) -> None:
        t = Log1pTransform()
        assert t.apply(0.0) == pytest.approx(0.0)
        assert t.apply(math.e - 1) == pytest.approx(1.0)
        assert t.name == "log1p"

    def test_bucketize_below_first(self) -> None:
        t = BucketizeTransform([10.0, 20.0, 30.0])
        assert t.apply(5.0) == 0.0

    def test_bucketize_above_last(self) -> None:
        t = BucketizeTransform([10.0, 20.0, 30.0])
        assert t.apply(99.0) == 3.0

    def test_bucketize_middle(self) -> None:
        t = BucketizeTransform([10.0, 20.0, 30.0])
        assert t.apply(15.0) == 1.0
        assert t.apply(25.0) == 2.0

    def test_bucketize_on_boundary(self) -> None:
        t = BucketizeTransform([10.0, 20.0])
        # value == boundary[0] → bucket 1 (not < 10)
        assert t.apply(10.0) == 1.0

    def test_bucketize_boundaries_sorted(self) -> None:
        t = BucketizeTransform([30.0, 10.0, 20.0])
        assert t.boundaries == [10.0, 20.0, 30.0]

    def test_lag_not_enough_history(self) -> None:
        t = LagTransform(n=3)
        assert math.isnan(t.apply(1.0))
        assert math.isnan(t.apply(2.0))
        assert math.isnan(t.apply(3.0))

    def test_lag_returns_n_steps_ago(self) -> None:
        t = LagTransform(n=2)
        t.apply(10.0)
        t.apply(20.0)
        result = t.apply(30.0)
        assert result == pytest.approx(10.0)

    def test_lag_reset(self) -> None:
        t = LagTransform(n=1)
        t.apply(1.0)
        t.apply(2.0)
        t.reset()
        assert math.isnan(t.apply(99.0))

    def test_lag_n_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            LagTransform(n=0)

    def test_get_transform_identity(self) -> None:
        t = get_transform("identity")
        assert isinstance(t, IdentityTransform)

    def test_get_transform_zscore(self) -> None:
        t = get_transform("zscore", mean=1.0, std=2.0)
        assert isinstance(t, ZScoreTransform)

    def test_get_transform_unknown_raises(self) -> None:
        with pytest.raises(ValueError):
            get_transform("nonexistent_transform")


# ---------------------------------------------------------------------------
# TestFeatureStore
# ---------------------------------------------------------------------------


class TestFeatureStore:
    def test_put_and_get_latest(self) -> None:
        fs = FeatureStore()
        fs.put("u1", "age", 25.0, _ts(0))
        assert fs.get("u1", "age") == 25.0

    def test_get_missing_returns_none(self) -> None:
        fs = FeatureStore()
        assert fs.get("unknown", "feat") is None

    def test_point_in_time_correct(self) -> None:
        fs = FeatureStore()
        fs.put("u1", "score", 10.0, _ts(0))
        fs.put("u1", "score", 20.0, _ts(10))
        fs.put("u1", "score", 30.0, _ts(20))
        # As of t=15 → latest value ≤ 15 is 20.0 (at t=10)
        assert fs.get("u1", "score", as_of_ts=_ts(15)) == 20.0

    def test_as_of_before_first_entry_returns_none(self) -> None:
        fs = FeatureStore()
        fs.put("u1", "score", 100.0, _ts(5))
        assert fs.get("u1", "score", as_of_ts=_ts(4)) is None

    def test_get_vector(self) -> None:
        fs = FeatureStore()
        fs.put("e1", "f1", 1.0, _ts(0))
        fs.put("e1", "f2", 2.0, _ts(0))
        fv = fs.get_vector("e1", ["f1", "f2"], as_of_ts=_ts(1))
        assert fv.features["f1"] == 1.0
        assert fv.features["f2"] == 2.0
        assert fv.entity_id == "e1"

    def test_get_vector_missing_feature(self) -> None:
        fs = FeatureStore()
        fs.put("e1", "f1", 7.0, _ts(0))
        fv = fs.get_vector("e1", ["f1", "f99"], as_of_ts=_ts(5))
        assert fv.features["f99"] is None

    def test_multiple_entities_independent(self) -> None:
        fs = FeatureStore()
        fs.put("u1", "x", 1.0, _ts(0))
        fs.put("u2", "x", 99.0, _ts(0))
        assert fs.get("u1", "x") == 1.0
        assert fs.get("u2", "x") == 99.0

    def test_overwrites_ordered_by_timestamp(self) -> None:
        fs = FeatureStore()
        fs.put("e", "f", 5.0, _ts(10))
        fs.put("e", "f", 3.0, _ts(5))  # inserted out-of-order
        # Latest overall = 5.0 (at t=10)
        assert fs.get("e", "f") == 5.0
        # As-of t=7 → 3.0 (at t=5)
        assert fs.get("e", "f", as_of_ts=_ts(7)) == 3.0

    def test_concurrent_writes(self) -> None:
        fs = FeatureStore()
        errors: list[Exception] = []

        def _write(i: int) -> None:
            try:
                fs.put("entity", f"feat_{i}", float(i), _ts(i))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_write, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert fs.feature_count() == 100

    def test_entity_count(self) -> None:
        fs = FeatureStore()
        fs.put("a", "f", 1.0, _ts(0))
        fs.put("b", "f", 2.0, _ts(0))
        assert fs.entity_count() == 2


# ---------------------------------------------------------------------------
# TestBatchProcessor
# ---------------------------------------------------------------------------


class TestBatchProcessor:
    def _write_jsonl(self, path: Path, records: list[dict]) -> None:  # type: ignore[type-arg]
        with path.open("w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")

    def test_basic_processing(self, tmp_path: Path) -> None:
        records = [
            {"entity_id": "u1", "ts": "2024-01-01", "age": 25.0},
            {"entity_id": "u2", "ts": "2024-01-02", "age": 30.0},
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        self._write_jsonl(inp, records)

        reg = FeatureRegistry()
        proc = BatchProcessor(reg)
        stats = proc.process(inp, out, feature_cols=["age"])

        assert out.exists()
        assert stats["age"].count == 2
        assert stats["age"].mean == pytest.approx(27.5)

    def test_transform_applied(self, tmp_path: Path) -> None:
        records = [{"entity_id": "u1", "ts": "t0", "val": 0.0}]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        self._write_jsonl(inp, records)

        from featstore.transforms import Log1pTransform

        reg = FeatureRegistry()
        proc = BatchProcessor(reg, transforms={"val": Log1pTransform()})
        proc.process(inp, out, feature_cols=["val"])

        with out.open() as fh:
            result = json.loads(fh.readline())
        assert result["val"] == pytest.approx(math.log1p(0.0))

    def test_histogram_buckets(self, tmp_path: Path) -> None:
        import random

        rng = random.Random(42)
        records = [
            {"entity_id": f"u{i}", "ts": "t0", "v": rng.uniform(0, 100)} for i in range(200)
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        self._write_jsonl(inp, records)

        reg = FeatureRegistry()
        proc = BatchProcessor(reg)
        stats = proc.process(inp, out, feature_cols=["v"])

        assert len(stats["v"].histogram) == 20
        total_in_buckets = sum(c for _, _, c in stats["v"].histogram)
        assert total_in_buckets == 200

    def test_write_and_load_stats(self, tmp_path: Path) -> None:
        records = [{"entity_id": "u1", "ts": "t0", "x": float(i)} for i in range(10)]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        stats_path = tmp_path / "stats.jsonl"
        self._write_jsonl(inp, records)

        reg = FeatureRegistry()
        proc = BatchProcessor(reg)
        stats = proc.process(inp, out, feature_cols=["x"])
        proc.write_stats(stats, stats_path)

        loaded = proc.load_stats(stats_path)
        assert "x" in loaded
        assert loaded["x"].count == 10
        assert loaded["x"].mean == pytest.approx(stats["x"].mean)

    def test_none_values_skipped(self, tmp_path: Path) -> None:
        records = [
            {"entity_id": "u1", "ts": "t0", "v": 5.0},
            {"entity_id": "u2", "ts": "t1", "v": None},
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        self._write_jsonl(inp, records)

        reg = FeatureRegistry()
        proc = BatchProcessor(reg)
        stats = proc.process(inp, out, feature_cols=["v"])
        assert stats["v"].count == 1

    def test_distribution_stats_min_max(self, tmp_path: Path) -> None:
        records = [{"entity_id": "u", "ts": "t0", "v": float(i)} for i in range(1, 6)]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        self._write_jsonl(inp, records)

        reg = FeatureRegistry()
        proc = BatchProcessor(reg)
        stats = proc.process(inp, out, feature_cols=["v"])
        assert stats["v"].min_val == pytest.approx(1.0)
        assert stats["v"].max_val == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# TestStreamProcessor
# ---------------------------------------------------------------------------


class TestStreamProcessor:
    def test_welford_mean(self) -> None:
        reg = FeatureRegistry()
        store = FeatureStore()
        sp = StreamProcessor(reg, store)
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for i, v in enumerate(values):
            sp.process_event("e", "x", v, _ts(i))
        stats = sp.get_stats("x")
        assert stats is not None
        assert stats.mean == pytest.approx(3.0)

    def test_welford_std(self) -> None:
        import statistics

        reg = FeatureRegistry()
        store = FeatureStore()
        sp = StreamProcessor(reg, store)
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        for i, v in enumerate(values):
            sp.process_event("e", "y", v, _ts(i))
        stats = sp.get_stats("y")
        assert stats is not None
        assert stats.std == pytest.approx(statistics.stdev(values), rel=1e-6)

    def test_online_store_updated(self) -> None:
        reg = FeatureRegistry()
        store = FeatureStore()
        sp = StreamProcessor(reg, store)
        sp.process_event("u1", "score", 42.0, _ts(0))
        assert store.get("u1", "score") == pytest.approx(42.0)

    def test_transform_applied_in_stream(self) -> None:
        reg = FeatureRegistry()
        store = FeatureStore()
        sp = StreamProcessor(reg, store, transforms={"v": Log1pTransform()})
        sp.process_event("e", "v", 0.0, _ts(0))
        assert store.get("e", "v") == pytest.approx(math.log1p(0.0))

    def test_multiple_features_independent_stats(self) -> None:
        reg = FeatureRegistry()
        store = FeatureStore()
        sp = StreamProcessor(reg, store)
        sp.process_event("e", "a", 10.0, _ts(0))
        sp.process_event("e", "b", 100.0, _ts(1))
        assert sp.get_stats("a") is not None
        assert sp.get_stats("b") is not None
        assert sp.get_stats("a").mean == pytest.approx(10.0)  # type: ignore[union-attr]
        assert sp.get_stats("b").mean == pytest.approx(100.0)  # type: ignore[union-attr]

    def test_get_stats_unknown_returns_none(self) -> None:
        reg = FeatureRegistry()
        store = FeatureStore()
        sp = StreamProcessor(reg, store)
        assert sp.get_stats("nonexistent") is None

    def test_all_stats(self) -> None:
        reg = FeatureRegistry()
        store = FeatureStore()
        sp = StreamProcessor(reg, store)
        sp.process_event("e", "f1", 1.0, _ts(0))
        sp.process_event("e", "f2", 2.0, _ts(1))
        all_s = sp.all_stats()
        assert set(all_s.keys()) == {"f1", "f2"}

    def test_running_stats_single_value_variance_zero(self) -> None:
        rs = RunningStats("x")
        rs.update(5.0)
        assert rs.variance == 0.0
        assert rs.std == 0.0


# ---------------------------------------------------------------------------
# TestSkewDetector
# ---------------------------------------------------------------------------


class TestSkewDetector:
    def _make_stats(self, values: list[float], name: str = "f") -> DistributionStats:
        ds = DistributionStats(name)
        for v in values:
            ds.update(v)
        ds.finalise(values)
        return ds

    def test_ks_identical_distributions_near_zero(self) -> None:
        samples = [float(i) for i in range(100)]
        ks = _ks_two_sample(samples, samples)
        assert ks == pytest.approx(0.0, abs=1e-6)

    def test_ks_completely_separated(self) -> None:
        a = [0.0, 1.0, 2.0]
        b = [10.0, 11.0, 12.0]
        ks = _ks_two_sample(a, b)
        assert ks > 0.5

    def test_ks_empty_returns_zero(self) -> None:
        assert _ks_two_sample([], [1.0, 2.0]) == 0.0
        assert _ks_two_sample([1.0], []) == 0.0

    def test_psi_identical_histograms_near_zero(self) -> None:
        hist = [(float(i), float(i + 1), 10) for i in range(20)]
        psi = _psi_from_histograms(hist, hist, 200, 200)
        assert psi == pytest.approx(0.0, abs=1e-3)

    def test_psi_different_histograms_positive(self) -> None:
        hist_a = [(float(i), float(i + 1), 100 if i < 10 else 1) for i in range(20)]
        hist_b = [(float(i), float(i + 1), 1 if i < 10 else 100) for i in range(20)]
        total_a = sum(c for _, _, c in hist_a)
        total_b = sum(c for _, _, c in hist_b)
        psi = _psi_from_histograms(hist_a, hist_b, total_a, total_b)
        assert psi > 0.1

    def test_no_alert_similar_distributions(self) -> None:
        samples = [float(i) for i in range(100)]
        batch = self._make_stats(samples)
        stream = self._make_stats(samples)
        detector = SkewDetector(ks_threshold=0.1, psi_threshold=0.2)
        report = detector.check(batch, stream, batch_samples=samples, stream_samples=samples)
        assert not report.alert

    def test_alert_raised_on_shifted_distribution(self) -> None:
        batch_samples = [float(i) for i in range(100)]
        stream_samples = [float(i) + 50.0 for i in range(100)]
        batch = self._make_stats(batch_samples)
        stream = self._make_stats(stream_samples, name="f")
        detector = SkewDetector(ks_threshold=0.1, psi_threshold=0.2)
        with pytest.raises(SkewAlert) as exc_info:
            detector.check(
                batch, stream, batch_samples=batch_samples, stream_samples=stream_samples
            )
        assert exc_info.value.report.ks_statistic > 0.1

    def test_skew_report_to_dict(self) -> None:
        samples = [float(i) for i in range(50)]
        batch = self._make_stats(samples)
        stream = self._make_stats(samples)
        detector = SkewDetector()
        report = detector.check(batch, stream, batch_samples=samples, stream_samples=samples)
        d = report.to_dict()
        assert "ks_statistic" in d
        assert "psi" in d
        assert "alert" in d

    def test_psi_empty_histograms_returns_zero(self) -> None:
        assert _psi_from_histograms([], [], 0, 0) == 0.0

    def test_psi_mismatched_histogram_lengths_returns_zero(self) -> None:
        h1 = [(0.0, 1.0, 5)]
        h2 = [(0.0, 1.0, 5), (1.0, 2.0, 3)]
        assert _psi_from_histograms(h1, h2, 5, 8) == 0.0


# ---------------------------------------------------------------------------
# TestProperties — Hypothesis-based
# ---------------------------------------------------------------------------


class TestProperties:
    @given(
        values=st.lists(st.floats(min_value=-1000, max_value=1000, allow_nan=False), min_size=1),
        offset=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=100)
    def test_point_in_time_never_returns_future(
        self,
        values: list[float],
        offset: int,
    ) -> None:
        """get(as_of_ts=T) must never return a value inserted at timestamp > T."""
        fs = FeatureStore()
        base = datetime(2024, 1, 1)
        for i, v in enumerate(values):
            ts = base + timedelta(seconds=i)
            fs.put("e", "f", v, ts)
        as_of = base + timedelta(seconds=offset)
        result = fs.get("e", "f", as_of_ts=as_of)
        if result is not None:
            # Find the timestamp of the returned value
            # The returned value should be one of the values at ts <= as_of
            eligible = {v for i, v in enumerate(values) if i <= offset}
            assert result in eligible

    @given(
        mean=st.floats(min_value=-100, max_value=100, allow_nan=False),
        std=st.floats(min_value=0.1, max_value=100, allow_nan=False),
        x=st.floats(min_value=-1000, max_value=1000, allow_nan=False),
    )
    @settings(max_examples=200)
    def test_zscore_inverse_roundtrip(
        self,
        mean: float,
        std: float,
        x: float,
    ) -> None:
        """ZScore(inverse(z)) ≈ x for all finite inputs with non-zero std."""
        t = ZScoreTransform(mean=mean, std=std)
        z = t.apply(x)
        recovered = t.inverse(z)
        assert recovered == pytest.approx(x, rel=1e-6, abs=1e-9)

    @given(
        values=st.lists(
            st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
            min_size=30,
            max_size=200,
        )
    )
    @settings(max_examples=50)
    def test_batch_stats_mean_converges(self, values: list[float]) -> None:
        """Batch processor's computed mean matches statistics.mean of input."""
        import statistics as _stats

        ds = DistributionStats("x")
        for v in values:
            ds.update(v)
        ds.finalise(values)
        assert ds.mean == pytest.approx(_stats.mean(values), rel=1e-6, abs=1e-9)

    @given(
        n=st.integers(min_value=1, max_value=10),
        values=st.lists(
            st.floats(min_value=0, max_value=100, allow_nan=False),
            min_size=1,
            max_size=30,
        ),
    )
    @settings(max_examples=100)
    def test_lag_buffer_never_returns_future(self, n: int, values: list[float]) -> None:
        """LagTransform(n).apply(v[i]) should equal v[i-n] when buffer is full."""
        t = LagTransform(n=n)
        results = [t.apply(v) for v in values]
        for i, r in enumerate(results):
            if i < n:
                assert math.isnan(r)
            else:
                assert r == pytest.approx(values[i - n])
