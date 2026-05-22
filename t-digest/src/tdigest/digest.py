"""Core t-digest operations — build, add, compress, merge, quantile, cdf.

Buffer-then-merge variant: ``add(v)`` is O(1); periodic ``compress()``
sorts (buffer ∪ centroids) by mean and greedily merges adjacent
centroids while their combined weight stays within
``scale.max_combined_weight(q_left, total, δ)``.

Quantile estimation uses **linear interpolation** between centroid
means. Within a centroid we assume the underlying values are uniformly
distributed across its cumulative-quantile span. The cdf at exactly
``min_value`` and ``max_value`` is pinned to 0 and 1 respectively
(Dunning's pinning trick).
"""

from __future__ import annotations

from tdigest.scale import max_combined_weight
from tdigest.schema import BuildableTDigest, Centroid, TDigest

_DEFAULT_BUFFER_FACTOR = 5  # buffer_size = factor * compression


def build(
    compression: float = 100.0,
    buffer_size: int | None = None,
) -> BuildableTDigest:
    """Construct an empty t-digest with the given compression parameter."""
    if compression < 1:
        raise ValueError(f"compression must be >= 1, got {compression}")
    bsize = buffer_size if buffer_size is not None else int(_DEFAULT_BUFFER_FACTOR * compression)
    return BuildableTDigest(compression=compression, buffer_size=max(1, bsize))


def add(td: BuildableTDigest, value: float, weight: float = 1.0) -> None:
    """Append a single ``(value, weight)`` event to the digest."""
    if weight <= 0:
        raise ValueError(f"weight must be > 0, got {weight}")
    if value != value:  # NaN guard
        raise ValueError("value must not be NaN")
    td._buffer.append(Centroid(mean=value, weight=weight))
    td.total_weight += weight
    if value < td.min_value:
        td.min_value = value
    if value > td.max_value:
        td.max_value = value
    if len(td._buffer) >= td.buffer_size:
        compress(td)


def compress(td: BuildableTDigest) -> None:
    """Merge any pending buffer into the centroid list under the size bound."""
    if not td._buffer and not td._centroids:
        return
    combined = sorted(td._centroids + td._buffer, key=lambda c: c.mean)
    td._buffer = []
    if not combined:
        return
    total = sum(c.weight for c in combined)
    if total <= 0:
        td._centroids = []
        return

    new_centroids: list[Centroid] = [combined[0]]
    cumulative = combined[0].weight
    q_left = 0.0

    for nxt in combined[1:]:
        # Cumulative quantile span occupied by the merge-target so far.
        cand_weight = new_centroids[-1].weight + nxt.weight
        # Allowed weight for a centroid starting at q_left.
        allowed = max_combined_weight(q_left, total, td.compression)
        if cand_weight <= allowed:
            # Merge nxt into the current super-centroid.
            cur = new_centroids[-1]
            merged_mean = (cur.mean * cur.weight + nxt.mean * nxt.weight) / cand_weight
            new_centroids[-1] = Centroid(mean=merged_mean, weight=cand_weight)
            cumulative += nxt.weight
        else:
            # Close out the current centroid; nxt starts a new one.
            q_left = cumulative / total
            new_centroids.append(nxt)
            cumulative += nxt.weight

    td._centroids = new_centroids
    td.total_weight = total


def merge(a: TDigest, b: TDigest) -> TDigest:
    """Combine two snapshots — exact, no information lost.

    Uses the smaller of the two ``compression`` values for the result.
    """
    compression = min(a.compression, b.compression)
    builder = build(compression=compression)
    for c in a.centroids:
        builder._buffer.append(c)
    for c in b.centroids:
        builder._buffer.append(c)
    builder.total_weight = a.total_weight + b.total_weight
    builder.min_value = min(a.min_value, b.min_value)
    builder.max_value = max(a.max_value, b.max_value)
    compress(builder)
    return freeze(builder)


def freeze(td: BuildableTDigest) -> TDigest:
    """Snapshot a mutable digest into an immutable ``TDigest``."""
    compress(td)
    return TDigest(
        compression=td.compression,
        centroids=tuple(td._centroids),
        total_weight=td.total_weight,
        min_value=td.min_value if td.total_weight > 0 else 0.0,
        max_value=td.max_value if td.total_weight > 0 else 0.0,
    )


def thaw(snapshot: TDigest, buffer_size: int | None = None) -> BuildableTDigest:
    """Rebuild a mutable digest from an immutable snapshot."""
    builder = build(compression=snapshot.compression, buffer_size=buffer_size)
    builder._centroids = list(snapshot.centroids)
    builder.total_weight = snapshot.total_weight
    builder.min_value = snapshot.min_value
    builder.max_value = snapshot.max_value
    return builder


# ---------- Queries ---------------------------------------------------------


def quantile(td: BuildableTDigest | TDigest, q: float) -> float:
    """Estimate the ``q``-th quantile (0 ≤ q ≤ 1) by linear centroid interpolation."""
    if not 0 <= q <= 1:
        raise ValueError(f"q must be in [0, 1], got {q}")
    centroids, total, vmin, vmax = _snapshot_view(td)
    if not centroids or total <= 0:
        raise ValueError("digest is empty")
    if q == 0:
        return vmin
    if q == 1:
        return vmax
    target = q * total
    # Build sorted (cumulative_midpoint, mean) pairs for interpolation.
    mids: list[tuple[float, float]] = []
    cum = 0.0
    for c in centroids:
        mids.append((cum + c.weight / 2, c.mean))
        cum += c.weight

    # Boundary sentinel points.
    lo_w, lo_v = 0.0, vmin
    hi_w, hi_v = total, vmax

    # Find the two adjacent anchor points that straddle target.
    all_points = [(lo_w, lo_v)] + mids + [(hi_w, hi_v)]
    for j in range(len(all_points) - 1):
        w0, v0 = all_points[j]
        w1, v1 = all_points[j + 1]
        if w0 <= target <= w1:
            span = max(w1 - w0, 1e-15)
            frac = max(0.0, min(1.0, (target - w0) / span))
            # Use endpoints directly to avoid catastrophic cancellation when
            # |v1 - v0| is tiny relative to |v0| (e.g. v0=-1, v1≈0).
            if frac <= 0.0:
                return v0
            if frac >= 1.0:
                return v1
            return v0 + frac * (v1 - v0)
    return vmax


def cdf(td: BuildableTDigest | TDigest, value: float) -> float:
    """Estimate the cumulative density at ``value`` (cdf inverse of ``quantile``)."""
    centroids, total, vmin, vmax = _snapshot_view(td)
    if not centroids or total <= 0:
        raise ValueError("digest is empty")
    if value < vmin:
        return 0.0
    if value > vmax:
        return 1.0
    if value == vmin == vmax:
        return 1.0
    cumulative = 0.0
    for i, c in enumerate(centroids):
        next_cum = cumulative + c.weight
        if value < c.mean:
            # value falls below this centroid's mean.
            if i == 0:
                frac = (value - vmin) / max(c.mean - vmin, 1e-12)
                return (frac * c.weight / 2) / total
            prev = centroids[i - 1]
            prev_centre = cumulative - prev.weight / 2
            this_centre = cumulative + c.weight / 2
            frac = (value - prev.mean) / max(c.mean - prev.mean, 1e-12)
            cum_pos = prev_centre + frac * (this_centre - prev_centre)
            return cum_pos / total
        if value == c.mean:
            return (cumulative + c.weight / 2) / total
        cumulative = next_cum
    # value above all centroid means → interpolate from last to max.
    last = centroids[-1]
    last_centre = total - last.weight / 2
    if value >= vmax:
        return 1.0
    frac = (value - last.mean) / max(vmax - last.mean, 1e-12)
    cum_pos = last_centre + frac * (total - last_centre)
    return cum_pos / total


def _snapshot_view(
    td: BuildableTDigest | TDigest,
) -> tuple[list[Centroid] | tuple[Centroid, ...], float, float, float]:
    """Materialize centroid list + metadata for query access."""
    if isinstance(td, BuildableTDigest):
        if td._buffer:
            compress(td)
        return td._centroids, td.total_weight, td.min_value, td.max_value
    return td.centroids, td.total_weight, td.min_value, td.max_value


__all__ = [
    "add",
    "build",
    "cdf",
    "compress",
    "freeze",
    "merge",
    "quantile",
    "thaw",
]
