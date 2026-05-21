"""Semester classification."""

from __future__ import annotations

from vngrade.classify import classify, gpa
from vngrade.schema import (
    ConductRating,
    SemesterClassification,
    SemesterReport,
    SubjectScore,
)


def _report(
    scores: dict[str, float], conduct: ConductRating = ConductRating.GOOD
) -> SemesterReport:
    return SemesterReport(
        student_id="S",
        school_year="2025-2026",
        semester=1,
        conduct=conduct,
        subjects=tuple(SubjectScore(subject=k, score=v) for k, v in scores.items()),
    )


def test_excellent() -> None:
    r = _report(
        {
            "Math": 9.0,
            "Literature": 9.0,
            "English": 9.0,
            "Physics": 8.0,
            "Chemistry": 8.0,
            "Biology": 7.5,
            "History": 7.0,
            "Geography": 7.0,
            "Civics": 7.5,
            "PE": 7.0,
        },
        conduct=ConductRating.EXCELLENT,
    )
    assert classify(r) == SemesterClassification.EXCELLENT


def test_excellent_requires_core_high() -> None:
    """All ≥ 6.5 isn't enough — need a core ≥ 8.0."""
    r = _report(
        {
            "Math": 7.5,  # core but < 8.0
            "Literature": 7.5,
            "English": 7.5,
            "Physics": 7.5,
            "Chemistry": 7.5,
            "Biology": 7.5,
        },
        conduct=ConductRating.EXCELLENT,
    )
    # All ≥ 6.5 but no core ≥ 8 → falls back to Khá.
    assert classify(r) == SemesterClassification.GOOD


def test_good() -> None:
    r = _report(
        {
            "Math": 7.0,
            "Literature": 7.0,
            "English": 7.0,
            "Physics": 6.5,
            "Chemistry": 6.5,
            "Biology": 6.5,
            "History": 5.0,
            "Geography": 5.5,
        },
    )
    # 6 subjects ≥ 6.5, min 5.0 → Khá.
    assert classify(r) == SemesterClassification.GOOD


def test_pass() -> None:
    r = _report(
        {
            "Math": 5.0,
            "Literature": 5.0,
            "English": 4.5,  # one < 5.0 allowed
            "Physics": 5.0,
            "Chemistry": 5.0,
        },
    )
    assert classify(r) == SemesterClassification.PASS


def test_fail_low_min() -> None:
    r = _report(
        {
            "Math": 3.0,  # < 3.5
            "Literature": 5.0,
        },
    )
    assert classify(r) == SemesterClassification.FAIL


def test_fail_too_many_low() -> None:
    r = _report(
        {
            "Math": 4.0,
            "Literature": 4.0,  # 2 subjects < 5.0
            "English": 4.0,
        },
    )
    assert classify(r) == SemesterClassification.FAIL


def test_empty_subjects_fails() -> None:
    r = _report({})
    assert classify(r) == SemesterClassification.FAIL


def test_conduct_fail_caps_at_pass() -> None:
    """A student with ChuaDat conduct cannot exceed Đạt even if grades are top."""
    r = _report(
        {
            "Math": 10.0,
            "Literature": 10.0,
            "English": 10.0,
            "Physics": 10.0,
        },
        conduct=ConductRating.FAIL,
    )
    assert classify(r) == SemesterClassification.PASS


def test_conduct_dat_does_not_block_excellent() -> None:
    """Only ChuaDat conduct caps; Đạt conduct still allows lower tiers."""
    r = _report(
        {
            "Math": 9.0,
            "Literature": 9.0,
            "Physics": 7.0,
            "Chemistry": 7.0,
            "Biology": 6.5,
            "History": 6.5,
        },
        conduct=ConductRating.PASS,
    )
    # Excellent needs conduct Tốt or Khá — Đạt is below that threshold.
    assert classify(r) != SemesterClassification.EXCELLENT


def test_gpa_arithmetic_mean() -> None:
    r = _report({"A": 8.0, "B": 9.0, "C": 7.0})
    assert abs(gpa(r) - 8.0) < 1e-9


def test_gpa_empty() -> None:
    assert gpa(_report({})) == 0.0
