"""Top-level profile builder.

``collect_profile()`` is the canonical entry point: feed it raw
string values + a declared ``ColumnKind``, get back a
``ColumnProfile`` with everything the downstream system needs.

For ``NUMERIC`` columns we also build a histogram (default
``EQUI_DEPTH`` since that's what query optimizers want).
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from colstats.categorical import cardinality, top_k
from colstats.histogram import equi_depth, equi_width, maxdiff
from colstats.numeric import numeric_stats
from colstats.schema import (
    ColumnKind,
    ColumnProfile,
    HistogramKind,
    StringStats,
    TopKEntry,
)

if TYPE_CHECKING:
    from colstats.schema import Histogram


_DEFAULT_TOPK = 10
_DEFAULT_HIST_BINS = 10
_DEFAULT_CARDINALITY_CAP = 10_000


def collect_profile(
    name: str,
    values: list[str],
    *,
    kind: ColumnKind,
    top_k_size: int = _DEFAULT_TOPK,
    histogram_kind: HistogramKind = HistogramKind.EQUI_DEPTH,
    histogram_bins: int = _DEFAULT_HIST_BINS,
    cardinality_cap: int = _DEFAULT_CARDINALITY_CAP,
) -> ColumnProfile:
    """Build a ``ColumnProfile`` over ``values``.

    Empty / null values are skipped for stats computation but counted
    toward ``n_rows``. A value is considered null when it's the
    empty string ``""``.
    """
    n_rows = len(values)
    non_null = [v for v in values if v]
    n_non_null = len(non_null)
    card, capped = cardinality(non_null, cap=cardinality_cap)

    numeric = None
    histogram: Histogram | None = None
    strings = None
    top_k_entries: tuple[TopKEntry, ...] = ()

    if kind is ColumnKind.NUMERIC:
        parsed = _parse_numeric(non_null)
        numeric = numeric_stats(parsed) if parsed else None
        if parsed:
            histogram = _build_histogram(parsed, histogram_kind, histogram_bins)
    elif kind is ColumnKind.DATE:
        # Treat dates as numeric via ordinal day offsets.
        parsed = _parse_date(non_null)
        numeric = numeric_stats(parsed) if parsed else None
        if parsed:
            histogram = _build_histogram(parsed, histogram_kind, histogram_bins)
    elif kind is ColumnKind.CATEGORICAL:
        top_k_entries = tuple(top_k(non_null, k=top_k_size))
    elif kind is ColumnKind.STRING:
        strings = _string_stats(non_null)
        top_k_entries = tuple(top_k(non_null, k=top_k_size))

    return ColumnProfile(
        name=name,
        kind=kind,
        n_rows=n_rows,
        n_non_null=n_non_null,
        cardinality=card,
        cardinality_capped=capped,
        numeric=numeric,
        strings=strings,
        top_k=top_k_entries,
        histogram=histogram,
    )


def _build_histogram(
    values: list[float],
    kind: HistogramKind,
    n_bins: int,
) -> Histogram:
    """Dispatch to the right histogram constructor."""
    if kind is HistogramKind.EQUI_WIDTH:
        return equi_width(values, n_bins=n_bins)
    if kind is HistogramKind.EQUI_DEPTH:
        return equi_depth(values, n_bins=n_bins)
    if kind is HistogramKind.MAXDIFF:
        return maxdiff(values, n_bins=n_bins)
    raise ValueError(f"unknown histogram kind: {kind}")


def _parse_numeric(values: list[str]) -> list[float]:
    """Best-effort parse of ``values`` as floats; drops failures."""
    out: list[float] = []
    for v in values:
        with contextlib.suppress(ValueError):
            out.append(float(v))
    return out


def _parse_date(values: list[str]) -> list[float]:
    """Parse ISO dates / datetimes to float day-offset from epoch."""
    from datetime import date, datetime

    out: list[float] = []
    epoch = date(1970, 1, 1)
    for v in values:
        with contextlib.suppress(ValueError):
            if "T" in v or " " in v:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                d = dt.date()
            else:
                d = date.fromisoformat(v)
            out.append((d - epoch).days)
    return out


def _string_stats(values: list[str]) -> StringStats:
    """min / max / mean string length."""
    if not values:
        return StringStats(min_length=0, max_length=0, mean_length=0.0)
    lengths = [len(v) for v in values]
    return StringStats(
        min_length=min(lengths),
        max_length=max(lengths),
        mean_length=sum(lengths) / len(lengths),
    )


__all__ = ["collect_profile"]
