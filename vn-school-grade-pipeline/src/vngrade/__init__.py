"""vn-school-grade-pipeline — MOET Circular 22 grade classifier."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

_LAZY: dict[str, tuple[str, str]] = {
    "ConductRating": ("vngrade.schema", "ConductRating"),
    "SemesterClassification": ("vngrade.schema", "SemesterClassification"),
    "SemesterReport": ("vngrade.schema", "SemesterReport"),
    "SubjectScore": ("vngrade.schema", "SubjectScore"),
    "classify": ("vngrade.classify", "classify"),
    "gpa": ("vngrade.classify", "gpa"),
    "generate": ("vngrade.simulator", "generate"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from vngrade.classify import classify, gpa
    from vngrade.schema import (
        ConductRating,
        SemesterClassification,
        SemesterReport,
        SubjectScore,
    )
    from vngrade.simulator import generate

__all__ = [
    "ConductRating",
    "SemesterClassification",
    "SemesterReport",
    "SubjectScore",
    "__version__",
    "classify",
    "generate",
    "gpa",
]
