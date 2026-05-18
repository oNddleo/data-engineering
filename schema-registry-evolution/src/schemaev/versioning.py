"""Suggest a semver bump from a list of FieldChanges.

The rule we apply:

* **MAJOR** — any BACKWARD-breaking change (removed required field,
  incompatible type change, …).
* **MINOR** — only safe additions (new fields with defaults, new
  aliases).
* **PATCH** — only metadata changes (default-value tweaks).

The output is one of ``("major", "minor", "patch", "none")``. ``"none"``
means no changes were observed — typically a re-publish of the same
schema.

We also compute the next version string from a starting point.
``next_version("1.2.3", "minor") → "1.3.0"`` etc.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from schemaev.compat import _classify_backward

if TYPE_CHECKING:
    from schemaev.schema import FieldChange


class BumpKind(str, Enum):
    """Four bump magnitudes."""

    NONE = "none"
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


def suggest_bump(changes: list[FieldChange]) -> BumpKind:
    """Pick the largest bump implied by the change set."""
    if not changes:
        return BumpKind.NONE
    has_minor = False
    has_patch = False
    for c in changes:
        if not _classify_backward(c):
            # Anything BACKWARD-breaking forces a MAJOR.
            return BumpKind.MAJOR
        if c.kind in ("ADDED", "ALIAS_ADDED"):
            has_minor = True
        elif c.kind in ("DEFAULT_CHANGED",):
            has_patch = True
        else:
            # REMOVED of optional, type widening — counted as MINOR.
            has_minor = True
    if has_minor:
        return BumpKind.MINOR
    if has_patch:
        return BumpKind.PATCH
    return BumpKind.NONE


def parse_semver(v: str) -> tuple[int, int, int]:
    """Parse ``"1.2.3"`` → ``(1, 2, 3)``. Rejects non-int parts."""
    parts = v.split(".")
    if len(parts) != 3:
        raise ValueError(f"version must be X.Y.Z, got {v!r}")
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as exc:
        raise ValueError(f"version parts must be integers, got {v!r}") from exc
    if major < 0 or minor < 0 or patch < 0:
        raise ValueError(f"version parts must be non-negative, got {v!r}")
    return major, minor, patch


def render_semver(major: int, minor: int, patch: int) -> str:
    return f"{major}.{minor}.{patch}"


def next_version(current: str, bump: BumpKind) -> str:
    """Apply ``bump`` to ``current``. ``NONE`` returns ``current`` unchanged."""
    major, minor, patch = parse_semver(current)
    if bump is BumpKind.MAJOR:
        return render_semver(major + 1, 0, 0)
    if bump is BumpKind.MINOR:
        return render_semver(major, minor + 1, 0)
    if bump is BumpKind.PATCH:
        return render_semver(major, minor, patch + 1)
    return current


__all__ = [
    "BumpKind",
    "next_version",
    "parse_semver",
    "render_semver",
    "suggest_bump",
]
