"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vngrade.classify import classify, gpa
from vngrade.schema import (
    ConductRating,
    SemesterClassification,
    SemesterReport,
    SubjectScore,
)

_score = st.integers(min_value=0, max_value=100).map(lambda x: round(x / 10, 1))
_subject = st.sampled_from(["Math", "Literature", "English", "Physics", "Chemistry"])


@given(
    scores=st.lists(_score, min_size=0, max_size=8),
    conduct=st.sampled_from(list(ConductRating)),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_classification_in_enum(scores: list[float], conduct: ConductRating) -> None:
    """classify() always returns a valid SemesterClassification."""
    subjects = tuple(SubjectScore(subject=f"S{i}", score=s) for i, s in enumerate(scores))
    r = SemesterReport(
        student_id="S",
        school_year="2025-2026",
        semester=1,
        conduct=conduct,
        subjects=subjects,
    )
    assert classify(r) in set(SemesterClassification)


@given(
    scores=st.lists(_score, min_size=1, max_size=8),
    conduct=st.sampled_from(list(ConductRating)),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_gpa_in_range(scores: list[float], conduct: ConductRating) -> None:
    subjects = tuple(SubjectScore(subject=f"S{i}", score=s) for i, s in enumerate(scores))
    r = SemesterReport(
        student_id="S",
        school_year="2025-2026",
        semester=1,
        conduct=conduct,
        subjects=subjects,
    )
    assert 0.0 <= gpa(r) <= 10.0


@given(
    scores=st.lists(_score, min_size=1, max_size=8),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_conduct_fail_caps_classification(scores: list[float]) -> None:
    """Conduct=FAIL always yields classification ≤ PASS."""
    subjects = tuple(SubjectScore(subject=f"S{i}", score=s) for i, s in enumerate(scores))
    r_fail = SemesterReport(
        student_id="S",
        school_year="2025-2026",
        semester=1,
        conduct=ConductRating.FAIL,
        subjects=subjects,
    )
    result = classify(r_fail)
    assert result in (SemesterClassification.FAIL, SemesterClassification.PASS)
