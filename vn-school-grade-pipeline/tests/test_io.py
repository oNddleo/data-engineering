"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from vngrade.io_jsonl import dump, load, report_from_dict, report_to_dict
from vngrade.schema import ConductRating, SemesterReport, SubjectScore


def _sample() -> SemesterReport:
    return SemesterReport(
        student_id="S-001",
        school_year="2025-2026",
        semester=1,
        conduct=ConductRating.GOOD,
        subjects=(
            SubjectScore(subject="Math", score=8.5),
            SubjectScore(subject="Literature", score=7.5),
            SubjectScore(subject="English", score=8.0),
        ),
    )


def test_report_roundtrip() -> None:
    r = _sample()
    assert report_from_dict(report_to_dict(r)) == r


def test_dump_load() -> None:
    assert load(dump([_sample()])) == [_sample()]


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")
