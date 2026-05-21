"""Deterministic synthetic semester-report generator."""

from __future__ import annotations

import random

from vngrade.schema import ConductRating, SemesterReport, SubjectScore

_SUBJECTS: tuple[str, ...] = (
    "Math",
    "Literature",
    "English",
    "Physics",
    "Chemistry",
    "Biology",
    "History",
    "Geography",
    "Civics",
    "PE",
)


def generate(n: int = 100, seed: int = 0) -> list[SemesterReport]:
    """Generate ``n`` synthetic semester reports."""
    if n < 0:
        raise ValueError("n must be >= 0")
    rng = random.Random(seed)
    out: list[SemesterReport] = []
    for i in range(n):
        # Sample a "talent level" per student: 0=struggling, 1=average, 2=top.
        bucket = rng.choices([0, 1, 2], weights=[2, 5, 2], k=1)[0]
        if bucket == 0:
            score_mean, score_std = 4.5, 1.5
            conduct_weights = [1, 3, 5, 2]  # mostly Đạt
        elif bucket == 1:
            score_mean, score_std = 6.5, 1.0
            conduct_weights = [2, 5, 4, 1]
        else:
            score_mean, score_std = 8.5, 0.7
            conduct_weights = [6, 3, 1, 0]  # mostly Tốt
        conduct = rng.choices(list(ConductRating), weights=conduct_weights, k=1)[0]

        subjects = tuple(
            SubjectScore(
                subject=name,
                score=round(max(0.0, min(10.0, rng.gauss(score_mean, score_std))) * 10) / 10,
            )
            for name in _SUBJECTS
        )
        out.append(
            SemesterReport(
                student_id=f"S-{i:06d}",
                school_year="2025-2026",
                semester=rng.choice([1, 2]),
                conduct=conduct,
                subjects=subjects,
            )
        )
    return out


__all__ = ["generate"]
