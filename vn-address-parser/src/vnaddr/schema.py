"""VN administrative-unit + parsed-address schema.

Vietnam's administrative hierarchy is three levels deep:

```
PROVINCE  (Tỉnh / Thành phố trực thuộc TW)   — 63 total
   │
   ├── DISTRICT  (Quận / Huyện / Thị xã / Thành phố thuộc tỉnh)
   │       │
   │       └── WARD  (Phường / Xã / Thị trấn)
```

Province codes follow ISO 3166-2:VN where applicable, otherwise the
TCTK 2-letter code (e.g. ``HCM``, ``HN``, ``DN``).

Match kinds distinguish how a token in raw input was associated with
an administrative unit:

| Kind         | Meaning                                                       |
| ------------ | ------------------------------------------------------------- |
| ``EXACT``    | Normalised input == unit's normalised canonical name.         |
| ``FUZZY``    | Edit distance <= threshold (typo tolerance).                  |
| ``ABBREV``   | Matched via abbreviation (``Q1`` → ``Quận 1``).               |
| ``MISSING``  | No match found at this level.                                 |
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AdminLevel(str, Enum):
    """Three VN administrative levels."""

    PROVINCE = "PROVINCE"
    DISTRICT = "DISTRICT"
    WARD = "WARD"


class MatchKind(str, Enum):
    """How a token was matched against the directory."""

    EXACT = "EXACT"
    FUZZY = "FUZZY"
    ABBREV = "ABBREV"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class AdminUnit:
    """One administrative unit at any level."""

    code: str  # e.g. "HCM:Q1:BNG" for HCM / Quận 1 / P. Bến Nghé
    name_vi: str  # canonical Vietnamese name with diacritics
    name_en: str  # romanized / English form
    level: AdminLevel
    parent_code: str = ""  # empty for PROVINCE
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("code must be non-empty")
        if not self.name_vi:
            raise ValueError("name_vi must be non-empty")
        if self.level is AdminLevel.PROVINCE and self.parent_code:
            raise ValueError("PROVINCE cannot have parent_code")
        if self.level is not AdminLevel.PROVINCE and not self.parent_code:
            raise ValueError(f"{self.level.value} must have parent_code")


@dataclass(frozen=True, slots=True)
class MatchedToken:
    """A single token from the input, mapped to an admin unit."""

    raw_token: str  # the original token from input
    matched_code: str  # AdminUnit.code, or "" if MISSING
    matched_name: str  # canonical name_vi, or "" if MISSING
    kind: MatchKind
    edit_distance: int = 0  # 0 for EXACT/ABBREV; ≥1 for FUZZY

    def __post_init__(self) -> None:
        if self.edit_distance < 0:
            raise ValueError("edit_distance must be >= 0")


@dataclass(frozen=True, slots=True)
class ParsedAddress:
    """The structured result of parsing one raw address string."""

    raw_input: str
    street: str = ""  # everything before the first matched admin unit
    ward: MatchedToken | None = None
    district: MatchedToken | None = None
    province: MatchedToken | None = None

    @property
    def is_complete(self) -> bool:
        """``True`` if all three admin levels were resolved."""
        return all(
            t is not None and t.kind is not MatchKind.MISSING
            for t in (self.ward, self.district, self.province)
        )

    @property
    def is_partial(self) -> bool:
        """``True`` if at least one admin level was resolved."""
        return any(
            t is not None and t.kind is not MatchKind.MISSING
            for t in (self.ward, self.district, self.province)
        )

    @property
    def normalised(self) -> str:
        """Reconstruct a clean canonical address string."""
        parts: list[str] = []
        if self.street:
            parts.append(self.street.strip())
        for t in (self.ward, self.district, self.province):
            if t is not None and t.matched_name:
                parts.append(t.matched_name)
        return ", ".join(parts)


__all__ = [
    "AdminLevel",
    "AdminUnit",
    "MatchKind",
    "MatchedToken",
    "ParsedAddress",
]
