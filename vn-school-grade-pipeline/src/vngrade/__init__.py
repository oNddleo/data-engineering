"""vn-school-grade-pipeline — MOET Circular 22 grade classifier."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "ConductRating": ("vngrade.schema", "ConductRating"),
        "SemesterClassification": ("vngrade.schema", "SemesterClassification"),
        "SemesterReport": ("vngrade.schema", "SemesterReport"),
        "SubjectScore": ("vngrade.schema", "SubjectScore"),
        "classify": ("vngrade.classify", "classify"),
        "gpa": ("vngrade.classify", "gpa"),
        "generate": ("vngrade.simulator", "generate"),
    }

    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
