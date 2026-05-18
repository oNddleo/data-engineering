"""Drift scores between two ``ColumnProfile``s.

Two canonical measures:

* **PSI (Population Stability Index)** — compares histograms of two
  populations bin-by-bin:

  ``PSI = sum_i (P_i - Q_i) * ln(P_i / Q_i)``

  where ``P_i``, ``Q_i`` are the fractions in bin ``i``. Standard
  thresholds: ``< 0.1`` stable, ``0.1-0.25`` minor shift, ``> 0.25``
  significant shift. Banking / credit-risk default.

* **KS (Kolmogorov-Smirnov) statistic** — max gap between empirical
  CDFs of the two populations:

  ``KS = sup_x |F_baseline(x) - F_compared(x)|``

  Range: ``[0, 1]``. Distribution-free, sensitive to shape changes.

Both functions return a single float drift score. Callers pick a
threshold based on their domain.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from colstats.schema import ColumnProfile


_EPSILON = 1e-4  # smoothing constant for PSI (avoids ln(0))


def psi(baseline: ColumnProfile, compared: ColumnProfile) -> float:
    """Compute PSI between the histograms of two profiles.

    Both profiles must have non-None histograms with the same
    ``n_bins`` and aligned bin boundaries. Raises ``ValueError``
    otherwise.

    Returns 0.0 for identical bin counts; rises with drift.
    """
    if baseline.histogram is None or compared.histogram is None:
        raise ValueError("both profiles must have histograms for PSI")
    if baseline.histogram.n_bins != compared.histogram.n_bins:
        raise ValueError(
            f"bin count mismatch: {baseline.histogram.n_bins} " f"vs {compared.histogram.n_bins}",
        )
    if baseline.histogram.total_count == 0 or compared.histogram.total_count == 0:
        return 0.0
    total_a = baseline.histogram.total_count
    total_b = compared.histogram.total_count
    score = 0.0
    for a_bin, b_bin in zip(
        baseline.histogram.bins,
        compared.histogram.bins,
        strict=True,
    ):
        p_a = max(a_bin.count / total_a, _EPSILON)
        p_b = max(b_bin.count / total_b, _EPSILON)
        score += (p_b - p_a) * math.log(p_b / p_a)
    return score


def ks(baseline: ColumnProfile, compared: ColumnProfile) -> float:
    """Compute KS statistic between two profiles' histograms.

    Approximated by walking bin-aligned CDFs. Requires matched bin
    boundaries (raises ``ValueError`` otherwise).
    """
    if baseline.histogram is None or compared.histogram is None:
        raise ValueError("both profiles must have histograms for KS")
    if baseline.histogram.n_bins != compared.histogram.n_bins:
        raise ValueError(
            f"bin count mismatch: {baseline.histogram.n_bins} " f"vs {compared.histogram.n_bins}",
        )
    total_a = baseline.histogram.total_count
    total_b = compared.histogram.total_count
    if total_a == 0 or total_b == 0:
        return 0.0
    cum_a = 0
    cum_b = 0
    max_gap = 0.0
    for a_bin, b_bin in zip(
        baseline.histogram.bins,
        compared.histogram.bins,
        strict=True,
    ):
        cum_a += a_bin.count
        cum_b += b_bin.count
        gap = abs(cum_a / total_a - cum_b / total_b)
        if gap > max_gap:
            max_gap = gap
    return max_gap


def psi_band(score: float) -> str:
    """Categorise a PSI score.

    Returns ``"stable"`` (< 0.1), ``"minor"`` (0.1–0.25), or
    ``"significant"`` (> 0.25). Standard credit-risk thresholds.
    """
    if score < 0.1:
        return "stable"
    if score < 0.25:
        return "minor"
    return "significant"


__all__ = ["ks", "psi", "psi_band"]
