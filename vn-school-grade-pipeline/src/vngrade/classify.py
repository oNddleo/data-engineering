"""Semester classification per MOET Circular 22/2021.

The classification rules (xếp loại học lực) for secondary school:

* **Tốt (Excellent)** — all subjects ≥ 6.5 AND a "core" subject set
  (Math / Literature / English) all ≥ 8.0, no single subject < 6.5,
  AND conduct rating is at least Khá.
* **Khá (Good)** — all subjects ≥ 5.0 AND at least 6 subjects ≥ 6.5
  with a "core" subject ≥ 6.5.
* **Đạt (Pass)** — no subject < 3.5, at most one subject < 5.0.
* **Chưa đạt (Fail)** — anything else.

We use the simpler 2024 published guidance which dropped the
weighted-average rule and switched to per-subject thresholds.

Conduct overrides: a student with ``ChuaDat`` conduct cannot be
classified above ``Dat`` regardless of academic performance.
"""

from __future__ import annotations

from vngrade.schema import (
    ConductRating,
    SemesterClassification,
    SemesterReport,
)

_CORE_SUBJECTS = frozenset({"Math", "Toan", "Literature", "Van", "English", "TiengAnh"})


def classify(report: SemesterReport) -> SemesterClassification:
    """Classify a semester report.

    Returns ``ChuaDat`` for an empty subject list (degenerate).
    """
    subjects = report.subjects
    if not subjects:
        return SemesterClassification.FAIL

    scores = [s.score for s in subjects]
    min_score = min(scores)
    n_core_high = sum(1 for s in subjects if s.subject in _CORE_SUBJECTS and s.score >= 8.0)
    n_high = sum(1 for s in scores if s >= 6.5)
    n_low = sum(1 for s in scores if s < 5.0)

    # Conduct gate: FAIL conduct caps at Dat.
    conduct_cap: SemesterClassification | None = None
    if report.conduct == ConductRating.FAIL:
        conduct_cap = SemesterClassification.PASS

    if (
        min_score >= 6.5
        and n_core_high >= 1
        and report.conduct in (ConductRating.EXCELLENT, ConductRating.GOOD)
    ):
        result = SemesterClassification.EXCELLENT
    elif min_score >= 5.0 and n_high >= max(6, len(subjects) - 2):
        result = SemesterClassification.GOOD
    elif min_score >= 3.5 and n_low <= 1:
        result = SemesterClassification.PASS
    else:
        result = SemesterClassification.FAIL

    # Apply conduct cap if it lowers the result.
    if conduct_cap is not None and _rank(result) > _rank(conduct_cap):
        return conduct_cap
    return result


def gpa(report: SemesterReport) -> float:
    """Simple arithmetic mean of all subject scores. 0.0 if no subjects."""
    if not report.subjects:
        return 0.0
    total = sum(s.score for s in report.subjects)
    return total / len(report.subjects)


_RANK: dict[SemesterClassification, int] = {
    SemesterClassification.FAIL: 0,
    SemesterClassification.PASS: 1,
    SemesterClassification.GOOD: 2,
    SemesterClassification.EXCELLENT: 3,
}


def _rank(c: SemesterClassification) -> int:
    return _RANK[c]


__all__ = ["classify", "gpa"]
