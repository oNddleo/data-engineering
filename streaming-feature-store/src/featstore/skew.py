"""Skew detection: KS statistic and PSI between batch and stream distributions."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from featstore.batch import DistributionStats


@dataclass
class SkewReport:
    """Result of a skew check between batch and stream distributions."""

    feature_name: str
    ks_statistic: float
    psi: float
    ks_threshold: float
    psi_threshold: float
    alert: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "ks_statistic": self.ks_statistic,
            "psi": self.psi,
            "ks_threshold": self.ks_threshold,
            "psi_threshold": self.psi_threshold,
            "alert": self.alert,
        }


class SkewAlert(Exception):
    """Raised when skew exceeds a configured threshold."""

    def __init__(self, report: SkewReport) -> None:
        self.report = report
        super().__init__(
            f"Skew alert for '{report.feature_name}': "
            f"KS={report.ks_statistic:.4f} PSI={report.psi:.4f}"
        )


def _ks_two_sample(a: list[float], b: list[float]) -> float:
    """Compute the two-sample KS statistic between samples *a* and *b*.

    Returns 0.0 if either sample is empty.
    """
    if not a or not b:
        return 0.0
    sa = sorted(a)
    sb = sorted(b)
    na = len(sa)
    nb = len(sb)
    # Merge and walk both ECDFs
    i = j = 0
    max_diff = 0.0
    while i < na and j < nb:
        if sa[i] < sb[j]:
            i += 1
        elif sb[j] < sa[i]:
            j += 1
        else:
            i += 1
            j += 1
        ecdf_a = i / na
        ecdf_b = j / nb
        diff = abs(ecdf_a - ecdf_b)
        if diff > max_diff:
            max_diff = diff
    return max_diff


def _psi_from_histograms(
    batch_hist: list[tuple[float, float, int]],
    stream_hist: list[tuple[float, float, int]],
    batch_total: int,
    stream_total: int,
    eps: float = 1e-8,
) -> float:
    """Compute PSI from aligned histogram bucket counts.

    PSI = sum( (stream% - batch%) * ln(stream% / batch%) )
    Histograms must have the same number of buckets; if sizes differ, returns 0.
    """
    if not batch_hist or not stream_hist or len(batch_hist) != len(stream_hist):
        return 0.0
    if batch_total <= 0 or stream_total <= 0:
        return 0.0
    psi = 0.0
    for (_, _, bc), (_, _, sc) in zip(batch_hist, stream_hist, strict=False):
        p_batch = bc / batch_total + eps
        p_stream = sc / stream_total + eps
        psi += (p_stream - p_batch) * math.log(p_stream / p_batch)
    return psi


class SkewDetector:
    """Compute KS and PSI between batch (offline) and stream (online) distributions."""

    def __init__(
        self,
        ks_threshold: float = 0.1,
        psi_threshold: float = 0.2,
    ) -> None:
        self._ks_threshold = ks_threshold
        self._psi_threshold = psi_threshold

    def check(
        self,
        batch_stats: DistributionStats,
        stream_stats: DistributionStats,
        batch_samples: list[float] | None = None,
        stream_samples: list[float] | None = None,
    ) -> SkewReport:
        """Compare *batch_stats* vs *stream_stats* and return a SkewReport.

        If raw samples are provided the KS statistic is computed from them;
        otherwise it falls back to a histogram-based approximation (less accurate).
        Raises SkewAlert if KS > ks_threshold or PSI > psi_threshold.
        """
        if batch_samples is not None and stream_samples is not None:
            ks = _ks_two_sample(batch_samples, stream_samples)
        else:
            # Approximate KS from distribution means / stds
            mean_diff = abs(batch_stats.mean - stream_stats.mean)
            pooled_std = max(
                (batch_stats.std + stream_stats.std) / 2.0, 1e-8
            )
            ks = min(mean_diff / pooled_std, 1.0)

        psi = _psi_from_histograms(
            batch_stats.histogram,
            stream_stats.histogram,
            batch_stats.count,
            stream_stats.count,
        )

        alert = ks > self._ks_threshold or psi > self._psi_threshold
        report = SkewReport(
            feature_name=batch_stats.feature_name,
            ks_statistic=ks,
            psi=psi,
            ks_threshold=self._ks_threshold,
            psi_threshold=self._psi_threshold,
            alert=alert,
        )
        if alert:
            raise SkewAlert(report)
        return report
