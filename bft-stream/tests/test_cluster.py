"""Integration tests for the BFT streaming cluster."""

from __future__ import annotations

import pytest

from bftstream.cluster import BFTCluster
from bftstream.schema import StreamRecord


def _records(window_id: int, count: int, value: float = 1.0) -> list[StreamRecord]:
    return [
        StreamRecord(timestamp=float(i), key=f"k{i}", value=value, window_id=window_id)
        for i in range(count)
    ]


class TestBFTCluster:
    def test_invalid_cluster_size(self) -> None:
        with pytest.raises(ValueError, match="3f\\+1"):
            BFTCluster(n_replicas=3, f=1)  # need 4 for f=1

    def test_creates_nodes(self) -> None:
        cluster = BFTCluster(n_replicas=4, f=1)
        assert len(cluster.replicas) == 4

    def test_window_committed_after_full_batch(self) -> None:
        cluster = BFTCluster(n_replicas=4, f=1, window_size=5)
        cluster.ingest_batch(_records(window_id=0, count=5))
        wins = cluster.committed_windows()
        assert len(wins) >= 1
        assert wins[0].window_id == 0
        assert wins[0].record_count == 5

    def test_all_honest_agree_after_full_batch(self) -> None:
        cluster = BFTCluster(n_replicas=4, f=1, window_size=5)
        cluster.ingest_batch(_records(window_id=0, count=5))
        assert cluster.all_honest_agree(0)

    def test_multiple_windows(self) -> None:
        cluster = BFTCluster(n_replicas=4, f=1, window_size=5)
        for wid in range(3):
            cluster.ingest_batch(_records(window_id=wid, count=5))
        wins = cluster.committed_windows()
        assert len(wins) == 3

    def test_watermark_advances(self) -> None:
        cluster = BFTCluster(n_replicas=4, f=1, window_size=5)
        cluster.ingest_batch(_records(window_id=0, count=5))
        assert cluster.watermark() == 0

    def test_byzantine_replica_does_not_block_progress(self) -> None:
        """f=1 Byzantine node: remaining 3 honest nodes still commit."""
        cluster = BFTCluster(n_replicas=4, f=1, window_size=5)
        cluster.make_byzantine("r3")
        cluster.ingest_batch(_records(window_id=0, count=5))
        wins = cluster.committed_windows("r0")
        assert len(wins) >= 1

    def test_value_sum_correct(self) -> None:
        cluster = BFTCluster(n_replicas=4, f=1, window_size=4)
        records = _records(window_id=0, count=4, value=2.5)
        cluster.ingest_batch(records)
        wins = cluster.committed_windows()
        assert wins[0].value_sum == pytest.approx(10.0)

    def test_larger_cluster(self) -> None:
        cluster = BFTCluster(n_replicas=7, f=2, window_size=3)
        cluster.ingest_batch(_records(window_id=0, count=3))
        assert cluster.all_honest_agree(0)

    def test_partial_window_not_committed(self) -> None:
        cluster = BFTCluster(n_replicas=4, f=1, window_size=10)
        # Only 5 records — window not full, no consensus triggered
        cluster.ingest_batch(_records(window_id=0, count=5))
        wins = cluster.committed_windows()
        assert len(wins) == 0
