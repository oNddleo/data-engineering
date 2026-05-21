"""VN school grade schema (MOET Circular 22/2021).

VN secondary schools use a **10-point scale** (thang điểm 10) for
written-exam subjects, and a 4-tier **assessment level** (Tốt / Khá /
Đạt / Chưa đạt) for non-exam subjects (PE, art, life-skills).

* ``Score`` — 0.0 to 10.0, one-decimal precision.
* ``ConductRating`` — Tốt / Khá / Đạt / Chưa đạt (the 2021 reform
  collapsed the older 5-tier Xuất sắc / Giỏi / Khá / Trung bình /
  Yếu scale into 4 tiers).
* ``SubjectScore`` — one subject's semester grade.
* ``SemesterReport`` — bundle of subject scores + conduct for a term.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConductRating(str, Enum):
    EXCELLENT = "Tot"  # Tốt
    GOOD = "Kha"  # Khá
    PASS = "Dat"  # Đạt
    FAIL = "ChuaDat"  # Chưa đạt


class SemesterClassification(str, Enum):
    """Overall semester classification per Circular 22/2021."""

    EXCELLENT = "Tot"  # all subjects >= 8.0, no subject < 6.5, conduct Tốt/Khá
    GOOD = "Kha"  # all subjects >= 6.5, no subject < 5.0
    PASS = "Dat"  # all subjects >= 5.0, no subject < 3.5
    FAIL = "ChuaDat"  # anything else


@dataclass(frozen=True, slots=True)
class SubjectScore:
    subject: str  # "Math", "Literature", "English", "Physics", …
    score: float  # 0.0 to 10.0, one-decimal precision

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("subject must be non-empty")
        if not 0.0 <= self.score <= 10.0:
            raise ValueError(f"score must be in [0, 10], got {self.score}")
        # Enforce one-decimal precision: 7.25 → invalid, 7.2 → ok.
        scaled = round(self.score * 10)
        if abs(self.score * 10 - scaled) > 1e-9:
            raise ValueError(f"score must have at most 1 decimal, got {self.score}")


@dataclass(frozen=True, slots=True)
class SemesterReport:
    student_id: str
    school_year: str  # e.g. "2025-2026"
    semester: int  # 1 or 2
    conduct: ConductRating
    subjects: tuple[SubjectScore, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.student_id:
            raise ValueError("student_id must be non-empty")
        if self.semester not in (1, 2):
            raise ValueError("semester must be 1 or 2")
        if not self.school_year:
            raise ValueError("school_year must be non-empty")
        # Subject names must be unique within a report.
        seen: set[str] = set()
        for s in self.subjects:
            if s.subject in seen:
                raise ValueError(f"duplicate subject: {s.subject!r}")
            seen.add(s.subject)


__all__ = [
    "ConductRating",
    "SemesterClassification",
    "SemesterReport",
    "SubjectScore",
]
