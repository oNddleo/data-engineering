"""Hypothesis property tests for BFT stream safety properties."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from bftstream.cluster import BFTCluster
from bftstream.schema import StreamRecord


def _records(window_id: int, count: int) -> list[StreamRecord]:
    return [
        StreamRecord(timestamp=float(i), key=f"k{i % 3}", value=float(i + 1), window_id=window_id)
        for i in range(count)
    ]


class TestBFTSafetyProperties:
    @given(
        n_extra=st.integers(min_value=0, max_value=3),
        seed=st.integers(min_value=0, max_value=99),
    )
    @settings(max_examples=20)
    def test_no_double_commit(self, n_extra: int, seed: int) -> None:
        """A window should be committed at most once per replica."""
        n = 4 + n_extra
        f = 1
        if n < 3 * f + 1:
            return
        cluster = BFTCluster(n_replicas=n, f=f, window_size=5)
        cluster.ingest_batch(_records(window_id=0, count=5))
        for rid, replica in cluster.replicas.items():
            window_ids = [w.window_id for w in replica.committed_windows]
            assert len(window_ids) == len(set(window_ids)), f"Double commit on {rid}"

    @given(
        n_windows=st.integers(min_value=1, max_value=4),
    )
    @settings(max_examples=20)
    def test_watermark_monotone(self, n_windows: int) -> None:
        """Watermark should only ever increase."""
        cluster = BFTCluster(n_replicas=4, f=1, window_size=5)
        prev_wm = -1
        for wid in range(n_windows):
            cluster.ingest_batch(_records(window_id=wid, count=5))
            wm = cluster.watermark()
            assert wm >= prev_wm
            prev_wm = wm

    @given(
        window_size=st.integers(min_value=3, max_value=8),
    )
    @settings(max_examples=20)
    def test_all_honest_agree_on_committed_window(self, window_size: int) -> None:
        """After full ingestion all honest replicas commit the same window."""
        cluster = BFTCluster(n_replicas=4, f=1, window_size=window_size)
        cluster.ingest_batch(_records(window_id=0, count=window_size))
        assert cluster.all_honest_agree(0)

    @given(
        n_windows=st.integers(min_value=1, max_value=3),
        value=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_value_sum_matches_ingested(self, n_windows: int, value: float) -> None:
        """Committed window value_sum should equal sum of ingested values."""
        ws = 4
        cluster = BFTCluster(n_replicas=4, f=1, window_size=ws)
        for wid in range(n_windows):
            records = [
                StreamRecord(timestamp=float(i), key="k", value=value, window_id=wid)
                for i in range(ws)
            ]
            cluster.ingest_batch(records)
        for win in cluster.committed_windows():
            import math

            assert math.isclose(win.value_sum, value * ws, rel_tol=1e-9)

    @given(
        n_nodes=st.integers(min_value=4, max_value=7),
    )
    @settings(max_examples=15)
    def test_progress_with_one_byzantine(self, n_nodes: int) -> None:
        """Cluster with 1 Byzantine node still commits (if n >= 4)."""
        if n_nodes < 4:
            return
        f = 1
        if n_nodes < 3 * f + 1:
            return
        cluster = BFTCluster(n_replicas=n_nodes, f=f, window_size=5)
        # Make the last node Byzantine
        cluster.make_byzantine(f"r{n_nodes - 1}")
        cluster.ingest_batch(_records(window_id=0, count=5))
        # Primary (r0) should have committed
        wins = cluster.committed_windows("r0")
        assert len(wins) >= 1
