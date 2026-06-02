"""EVN customer code directory + validation.

EVN customer codes are 13 characters: a 2-letter **provincial unit
prefix** (``PA``..``PE``..) followed by 11 digits. The prefix
identifies one of EVN's five regional corporations (Tổng Công ty
Điện lực):

| Prefix | Corporation       | Coverage                                |
| ------ | ----------------- | --------------------------------------- |
| PA     | EVNHANOI          | Thành phố Hà Nội                        |
| PB     | EVNNPC            | 27 northern provinces (excl. Hà Nội)    |
| PC     | EVNCPC            | 13 central provinces                    |
| PD     | EVNSPC            | 21 southern provinces (excl. HCMC)      |
| PE     | EVNHCMC           | Thành phố Hồ Chí Minh                   |

We validate the structural shape (PA-PE prefix + 11 digits) and
expose a provincial-unit lookup. The 11-digit numeric body is
operator-internal; we do not validate its checksum.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProvincialUnit:
    """One EVN regional power corporation."""

    prefix: str
    abbreviation: str
    name_vi: str
    name_en: str
    coverage_vi: str


_UNITS: tuple[ProvincialUnit, ...] = (
    ProvincialUnit(
        prefix="PA",
        abbreviation="EVNHANOI",
        name_vi="Tổng Công ty Điện lực TP Hà Nội",
        name_en="Hanoi Power Corporation",
        coverage_vi="Thành phố Hà Nội",
    ),
    ProvincialUnit(
        prefix="PB",
        abbreviation="EVNNPC",
        name_vi="Tổng Công ty Điện lực Miền Bắc",
        name_en="Northern Power Corporation",
        coverage_vi="27 tỉnh miền Bắc (trừ Hà Nội)",
    ),
    ProvincialUnit(
        prefix="PC",
        abbreviation="EVNCPC",
        name_vi="Tổng Công ty Điện lực Miền Trung",
        name_en="Central Power Corporation",
        coverage_vi="13 tỉnh miền Trung và Tây Nguyên",
    ),
    ProvincialUnit(
        prefix="PD",
        abbreviation="EVNSPC",
        name_vi="Tổng Công ty Điện lực Miền Nam",
        name_en="Southern Power Corporation",
        coverage_vi="21 tỉnh miền Nam (trừ TP HCM)",
    ),
    ProvincialUnit(
        prefix="PE",
        abbreviation="EVNHCMC",
        name_vi="Tổng Công ty Điện lực TP Hồ Chí Minh",
        name_en="Ho Chi Minh City Power Corporation",
        coverage_vi="Thành phố Hồ Chí Minh",
    ),
)


_BY_PREFIX: dict[str, ProvincialUnit] = {u.prefix: u for u in _UNITS}
_BY_ABBR: dict[str, ProvincialUnit] = {u.abbreviation: u for u in _UNITS}


def all_units() -> tuple[ProvincialUnit, ...]:
    return _UNITS


def unit_for_prefix(prefix: str) -> ProvincialUnit | None:
    """Look up a provincial unit by 2-letter prefix (case-insensitive)."""
    return _BY_PREFIX.get(prefix.upper())


def unit_for_abbr(abbr: str) -> ProvincialUnit | None:
    return _BY_ABBR.get(abbr.upper())


def is_valid_customer_code(code: str) -> bool:
    """``True`` iff ``code`` is exactly 2 prefix letters + 11 digits."""
    if not code or len(code) != 13:
        return False
    prefix = code[:2].upper()
    if prefix not in _BY_PREFIX:
        return False
    return code[2:].isdigit()


def unit_for_code(code: str) -> ProvincialUnit | None:
    """Resolve a customer code to its provincial unit, or ``None`` if invalid."""
    if not is_valid_customer_code(code):
        return None
    return _BY_PREFIX[code[:2].upper()]


__all__ = [
    "ProvincialUnit",
    "all_units",
    "is_valid_customer_code",
    "unit_for_abbr",
    "unit_for_code",
    "unit_for_prefix",
]
