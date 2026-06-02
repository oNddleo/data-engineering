"""JSONL codec for SemesterReport."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from vngrade.schema import ConductRating, SemesterReport, SubjectScore

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _require_float(d: dict[str, object], key: str) -> float:
    v = d[key]
    if not isinstance(v, int | float) or isinstance(v, bool):
        raise TypeError(f"{key} must be number, got {type(v).__name__}")
    return float(v)


def report_to_dict(r: SemesterReport) -> dict[str, object]:
    return {
        "student_id": r.student_id,
        "school_year": r.school_year,
        "semester": r.semester,
        "conduct": r.conduct.value,
        "subjects": [{"subject": s.subject, "score": s.score} for s in r.subjects],
    }


def report_from_dict(d: dict[str, object]) -> SemesterReport:
    raw_subjects = d.get("subjects", [])
    if not isinstance(raw_subjects, list):
        raise TypeError("subjects must be a list")
    subjects: list[SubjectScore] = []
    for raw in raw_subjects:
        if not isinstance(raw, dict):
            raise TypeError("each subject must be an object")
        subjects.append(
            SubjectScore(
                subject=_require_str(raw, "subject"),
                score=_require_float(raw, "score"),
            )
        )
    return SemesterReport(
        student_id=_require_str(d, "student_id"),
        school_year=_require_str(d, "school_year"),
        semester=_require_int(d, "semester"),
        conduct=ConductRating(_require_str(d, "conduct")),
        subjects=tuple(subjects),
    )


def dump(items: Iterable[SemesterReport]) -> str:
    return "\n".join(json.dumps(report_to_dict(r), ensure_ascii=False) for r in items) + "\n"


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(
                f"expected JSON object per line, got {type(parsed).__name__}",
            )
        yield parsed


def load(text: str) -> list[SemesterReport]:
    return [report_from_dict(d) for d in _iter_lines(text)]


__all__ = ["dump", "load", "report_from_dict", "report_to_dict"]
