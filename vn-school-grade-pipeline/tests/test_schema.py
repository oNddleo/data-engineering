"""Schema validation."""

from __future__ import annotations

import pytest

from vngrade.schema import ConductRating, SemesterReport, SubjectScore


def test_subject_basic() -> None:
    s = SubjectScore(subject="Math", score=8.5)
    assert s.subject == "Math"
    assert s.score == 8.5


def test_subject_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        SubjectScore(subject="", score=5.0)


@pytest.mark.parametrize("bad", [-0.1, 10.1, 11.0])
def test_subject_rejects_out_of_range(bad: float) -> None:
    with pytest.raises(ValueError):
        SubjectScore(subject="X", score=bad)


@pytest.mark.parametrize("bad", [7.25, 5.123, 9.99])
def test_subject_rejects_multi_decimal(bad: float) -> None:
    with pytest.raises(ValueError):
        SubjectScore(subject="X", score=bad)


@pytest.mark.parametrize("good", [0.0, 0.5, 5.0, 7.5, 9.9, 10.0])
def test_subject_accepts_one_decimal(good: float) -> None:
    s = SubjectScore(subject="X", score=good)
    assert s.score == good


def test_report_basic() -> None:
    r = SemesterReport(
        student_id="S-001",
        school_year="2025-2026",
        semester=1,
        conduct=ConductRating.GOOD,
        subjects=(SubjectScore(subject="Math", score=8.0),),
    )
    assert r.semester == 1


def test_report_rejects_empty_student() -> None:
    with pytest.raises(ValueError):
        SemesterReport(
            student_id="",
            school_year="2025-2026",
            semester=1,
            conduct=ConductRating.GOOD,
        )


@pytest.mark.parametrize("bad_sem", [0, 3, -1])
def test_report_rejects_bad_semester(bad_sem: int) -> None:
    with pytest.raises(ValueError):
        SemesterReport(
            student_id="S-001",
            school_year="2025-2026",
            semester=bad_sem,
            conduct=ConductRating.GOOD,
        )


def test_report_rejects_duplicate_subject() -> None:
    with pytest.raises(ValueError):
        SemesterReport(
            student_id="S-001",
            school_year="2025-2026",
            semester=1,
            conduct=ConductRating.GOOD,
            subjects=(
                SubjectScore(subject="Math", score=8.0),
                SubjectScore(subject="Math", score=7.0),
            ),
        )
