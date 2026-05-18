"""Three histogram-construction strategies.

| Strategy        | Bin boundary placement                                            |
| --------------- | ----------------------------------------------------------------- |
| ``EQUI_WIDTH``  | Linear spacing between min and max.                               |
| ``EQUI_DEPTH``  | Each bin holds ~ N/B values.                                      |
| ``MAXDIFF``     | Cut at the ``B-1`` largest gaps between adjacent sorted values.   |

Equi-width is simplest; equi-depth is the textbook query-optimizer
choice because it bounds per-bin frequency; MaxDiff (Poosala / Ioannidis
1996) is the best fit for **skewed** distributions because it concentrates
bins where values change quickly.

All three return a ``Histogram`` with ``B`` bins whose counts sum to
``len(values)`` (or to 0 for an empty input).
"""

from __future__ import annotations

from itertools import pairwise

from colstats.schema import Bin, Histogram, HistogramKind


def equi_width(values: list[float], n_bins: int = 10) -> Histogram:
    """Equal-width bins between min(values) and max(values)."""
    _check_n_bins(n_bins)
    if not values:
        return Histogram(kind=HistogramKind.EQUI_WIDTH, bins=(), total_count=0)
    lo, hi = min(values), max(values)
    if lo == hi:
        # Degenerate: all values equal → one bin with everything.
        bin_ = Bin(lower=lo, upper=lo, count=len(values))
        return Histogram(
            kind=HistogramKind.EQUI_WIDTH,
            bins=(bin_,),
            total_count=len(values),
        )
    width = (hi - lo) / n_bins
    bins_counts = [0] * n_bins
    for v in values:
        # Largest bin index is n_bins-1 (right edge is inclusive for max).
        idx = min(int((v - lo) / width), n_bins - 1)
        bins_counts[idx] += 1
    bins = tuple(
        Bin(lower=lo + i * width, upper=lo + (i + 1) * width, count=c)
        for i, c in enumerate(bins_counts)
    )
    return Histogram(kind=HistogramKind.EQUI_WIDTH, bins=bins, total_count=len(values))


def equi_depth(values: list[float], n_bins: int = 10) -> Histogram:
    """Equal-depth bins — each holding ~ N/B sorted values."""
    _check_n_bins(n_bins)
    if not values:
        return Histogram(kind=HistogramKind.EQUI_DEPTH, bins=(), total_count=0)
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    target = max(1, n // n_bins)
    bins: list[Bin] = []
    i = 0
    while i < n:
        end = min(i + target, n)
        # If this is the last bin, absorb any tail to make the count balance.
        if len(bins) == n_bins - 1:
            end = n
        lower = sorted_vals[i]
        upper = sorted_vals[end - 1]
        bins.append(Bin(lower=lower, upper=upper, count=end - i))
        i = end
    return Histogram(kind=HistogramKind.EQUI_DEPTH, bins=tuple(bins), total_count=n)


def maxdiff(values: list[float], n_bins: int = 10) -> Histogram:
    """MaxDiff bins — cut at the ``n_bins - 1`` largest gaps in sorted values.

    For very small inputs (fewer values than bins requested), we fall
    back to one-bin-per-distinct-value.
    """
    _check_n_bins(n_bins)
    if not values:
        return Histogram(kind=HistogramKind.MAXDIFF, bins=(), total_count=0)
    sorted_vals = sorted(values)
    distinct = sorted(set(sorted_vals))
    if len(distinct) <= n_bins:
        # One bin per distinct value.
        bins = tuple(
            Bin(
                lower=v,
                upper=v,
                count=sum(1 for x in sorted_vals if x == v),
            )
            for v in distinct
        )
        return Histogram(kind=HistogramKind.MAXDIFF, bins=bins, total_count=len(sorted_vals))

    # Compute gaps between distinct adjacent values.
    gaps: list[tuple[float, int]] = []
    for i in range(1, len(distinct)):
        gaps.append((distinct[i] - distinct[i - 1], i))
    gaps.sort(reverse=True)
    # Cut at the top (n_bins - 1) gaps.
    cut_indices = sorted(idx for _, idx in gaps[: n_bins - 1])

    bin_boundaries = [0, *cut_indices, len(distinct)]
    bins_list: list[Bin] = []
    for start, end in pairwise(bin_boundaries):
        lower = distinct[start]
        upper = distinct[end - 1]
        # Count = number of values falling in [lower, upper].
        count = sum(1 for v in sorted_vals if lower <= v <= upper)
        bins_list.append(Bin(lower=lower, upper=upper, count=count))
    return Histogram(
        kind=HistogramKind.MAXDIFF,
        bins=tuple(bins_list),
        total_count=len(sorted_vals),
    )


def reproject(values: list[float], template: Histogram) -> Histogram:
    """Re-bin ``values`` using the bin **edges** from ``template``.

    Useful for PSI / KS drift scoring where the compared sample must
    fall into the same bins as the baseline. Values below the first
    bin's lower edge fall into bin 0; values above the last bin's
    upper edge fall into the last bin.
    """
    if template.n_bins == 0:
        return Histogram(kind=template.kind, bins=(), total_count=0)
    bin_counts = [0] * template.n_bins
    edges = [b.lower for b in template.bins] + [template.bins[-1].upper]
    for v in values:
        idx = _bin_search(v, edges)
        bin_counts[idx] += 1
    new_bins = tuple(
        Bin(lower=template.bins[i].lower, upper=template.bins[i].upper, count=c)
        for i, c in enumerate(bin_counts)
    )
    return Histogram(kind=template.kind, bins=new_bins, total_count=len(values))


def _bin_search(value: float, edges: list[float]) -> int:
    """Return the bin index for ``value`` given a list of bin edges.

    Clamps to [0, len(edges)-2] so out-of-range values fall in the
    extreme bins.
    """
    n_bins = len(edges) - 1
    if value <= edges[0]:
        return 0
    if value >= edges[-1]:
        return n_bins - 1
    # Linear scan — n_bins is small (typically 10).
    for i in range(n_bins):
        if edges[i] <= value < edges[i + 1]:
            return i
    return n_bins - 1


def _check_n_bins(n_bins: int) -> None:
    if n_bins < 1:
        raise ValueError(f"n_bins must be >= 1, got {n_bins}")


__all__ = ["equi_depth", "equi_width", "maxdiff", "reproject"]
