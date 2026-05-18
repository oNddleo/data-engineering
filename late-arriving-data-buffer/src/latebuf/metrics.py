"""Run-end metrics computation over a buffer's lifetime."""

from __future__ import annotations

from statistics import median
from typing import TYPE_CHECKING

from latebuf.schema import BufferStats

if TYPE_CHECKING:
    from latebuf.buffer import LateArrivingBuffer


def compute_stats(buffer: LateArrivingBuffer) -> BufferStats:
    """Build a ``BufferStats`` snapshot of the buffer's lifetime."""
    lateness = buffer.lateness_observed
    if lateness:
        sorted_lateness = sorted(lateness)
        max_l = sorted_lateness[-1]
        med_l = int(median(sorted_lateness))
        p99_l = _percentile(sorted_lateness, 99)
    else:
        max_l = 0
        med_l = 0
        p99_l = 0
    return BufferStats(
        n_accepted=buffer.n_accepted,
        n_emitted=buffer.n_emitted,
        n_dead_lettered=buffer.n_dead_lettered,
        n_still_buffered=buffer.n_buffered,
        max_lateness_seconds=max_l,
        median_lateness_seconds=med_l,
        p99_lateness_seconds=p99_l,
        final_watermark=buffer.current_watermark,
    )


def _percentile(sorted_vals: list[int], pct: int) -> int:
    """Nearest-rank percentile on a pre-sorted list."""
    if not sorted_vals:
        return 0
    rank = max(1, int(round(pct / 100 * len(sorted_vals))))
    return sorted_vals[min(len(sorted_vals), rank) - 1]


__all__ = ["compute_stats"]
