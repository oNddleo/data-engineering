"""Count-Min sketch core — update / estimate / merge.

| Operation     | Cost     | Behaviour                                            |
| ------------- | -------- | ---------------------------------------------------- |
| ``update``    | O(d)     | hash to ``d`` cells, increment by ``count``.         |
| ``estimate``  | O(d)     | return ``min`` of the ``d`` cells (one-sided over).  |
| ``merge``     | O(d × w) | element-wise add of two same-shape sketches.         |

The min-trick: each row over-estimates independently (because of
hash collisions); the minimum across rows is the tightest
over-estimate consistent with the observations. The bound holds
with probability ≥ 1 − δ.
"""

from __future__ import annotations

from dataclasses import replace

from cms.hash import index_for
from cms.schema import (
    MAX_COUNT,
    CountMinSketch,
    SketchConfig,
    SketchStats,
)


def new_sketch(
    config: SketchConfig | None = None,
) -> CountMinSketch:
    """Construct a fresh empty sketch at the given config."""
    return CountMinSketch(config=config or SketchConfig())


def update(
    sketch: CountMinSketch,
    value: str | bytes | int | float,
    count: int = 1,
) -> CountMinSketch:
    """Increment counters for ``value`` by ``count``.

    Returns a *new* sketch with the updated counters and bumped
    ``total_count``. Mutates the internal rows in place (the
    dataclass is frozen but its list contents aren't).
    """
    if count < 0:
        raise ValueError(f"count must be >= 0, got {count}")
    if count == 0:
        return sketch
    w = sketch.width
    for row_idx, row in enumerate(sketch.rows):
        col = index_for(value, seed=row_idx, width=w)
        # Saturate at MAX_COUNT to keep counters in uint32.
        row[col] = min(MAX_COUNT, row[col] + count)
    new_total = min(MAX_COUNT, sketch.total_count + count)
    return replace(sketch, total_count=new_total)


def estimate(
    sketch: CountMinSketch,
    value: str | bytes | int | float,
) -> int:
    """Return the over-estimated count for ``value``."""
    w = sketch.width
    return min(
        row[index_for(value, seed=row_idx, width=w)] for row_idx, row in enumerate(sketch.rows)
    )


def merge(*sketches: CountMinSketch) -> CountMinSketch:
    """Return a sketch whose counters are the element-wise sum of all inputs.

    All sketches must have the same ``config`` (width × depth).
    """
    if not sketches:
        return new_sketch()
    first = sketches[0]
    config = first.config
    if any(s.config != config for s in sketches[1:]):
        raise ValueError("all sketches must share the same config")
    new_rows = [list(row) for row in first.rows]
    new_total = first.total_count
    for other in sketches[1:]:
        for r_idx, row in enumerate(other.rows):
            for c_idx, c in enumerate(row):
                new_rows[r_idx][c_idx] = min(
                    MAX_COUNT,
                    new_rows[r_idx][c_idx] + c,
                )
        new_total = min(MAX_COUNT, new_total + other.total_count)
    return CountMinSketch(config=config, rows=new_rows, total_count=new_total)


def stats(sketch: CountMinSketch) -> SketchStats:
    """Build a ``SketchStats`` snapshot."""
    max_counter = 0
    for row in sketch.rows:
        for c in row:
            if c > max_counter:
                max_counter = c
    return SketchStats(
        width=sketch.width,
        depth=sketch.depth,
        n_cells=sketch.n_cells,
        total_count=sketch.total_count,
        max_counter=max_counter,
        epsilon=sketch.config.epsilon,
        delta=sketch.config.delta,
        standard_error_bound=int(sketch.config.epsilon * sketch.total_count),
    )


__all__ = ["estimate", "merge", "new_sketch", "stats", "update"]
