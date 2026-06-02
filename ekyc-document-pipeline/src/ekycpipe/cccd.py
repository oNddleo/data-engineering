"""CCCD parser.

A 12-digit CCCD encodes four things:

* digits 1–3 — ``province_code`` of the place of *birth registration*
  (not residence). Must be in :data:`ekycpipe.provinces.PROVINCE_CODES`.
* digit 4 — combined gender + century:

  | digit | gender | century |
  | ----- | ------ | ------- |
  | 0     | MALE   | 19xx    |
  | 1     | FEMALE | 19xx    |
  | 2     | MALE   | 20xx    |
  | 3     | FEMALE | 20xx    |
  | 4     | MALE   | 21xx    |
  | 5     | FEMALE | 21xx    |
  | 6     | MALE   | 22xx    |
  | 7     | FEMALE | 22xx    |
  | 8     | MALE   | 23xx    |
  | 9     | FEMALE | 23xx    |

* digits 5–6 — last two digits of birth year (``YY``)
* digits 7–12 — six-digit serial within (province, century, year, gender).

Old 9-digit CMND uses a completely different layout and is not
handled here. Detect by length and reject (or fall through to a
separate parser if you ever add one).
"""

from __future__ import annotations

from ekycpipe.provinces import is_valid_province_code
from ekycpipe.schema import CCCDFields, Gender


class CCCDFormatError(ValueError):
    """The CCCD string is not a valid 12-digit Vietnamese CCCD."""


_GENDER_CENTURY: dict[int, tuple[Gender, int]] = {
    0: (Gender.MALE, 19),
    1: (Gender.FEMALE, 19),
    2: (Gender.MALE, 20),
    3: (Gender.FEMALE, 20),
    4: (Gender.MALE, 21),
    5: (Gender.FEMALE, 21),
    6: (Gender.MALE, 22),
    7: (Gender.FEMALE, 22),
    8: (Gender.MALE, 23),
    9: (Gender.FEMALE, 23),
}


def parse_cccd(cccd: str) -> CCCDFields:
    """Parse a 12-digit CCCD string into its four components.

    Raises :class:`CCCDFormatError` on any malformed input — wrong
    length, non-digit characters, unknown province code.
    """
    s = cccd.strip()
    if len(s) != 12:
        raise CCCDFormatError(f"CCCD must be 12 digits, got {len(s)}: {cccd!r}")
    if not s.isdigit():
        raise CCCDFormatError(f"CCCD must be all digits, got {cccd!r}")
    province = s[0:3]
    if not is_valid_province_code(province):
        raise CCCDFormatError(f"unknown province code {province!r} in CCCD {cccd!r}")
    gc_digit = int(s[3])
    gender, century = _GENDER_CENTURY[gc_digit]
    yy = int(s[4:6])
    serial = s[6:]
    return CCCDFields(
        province_code=province,
        gender=gender,
        century=century,
        birth_year_yy=yy,
        serial=serial,
    )


def build_cccd(
    *,
    province_code: str,
    gender: Gender,
    birth_year: int,
    serial: str,
) -> str:
    """Inverse of :func:`parse_cccd` — assemble a 12-digit CCCD string."""
    if not is_valid_province_code(province_code):
        raise CCCDFormatError(f"unknown province code {province_code!r}")
    if birth_year < 1900 or birth_year > 2399:
        raise CCCDFormatError(f"birth_year out of supported range 1900–2399: {birth_year}")
    if len(serial) != 6 or not serial.isdigit():
        raise CCCDFormatError(f"serial must be 6 digits, got {serial!r}")
    century = birth_year // 100
    yy = birth_year % 100
    # Reverse the table.
    gc_digit = next(d for d, (g, c) in _GENDER_CENTURY.items() if g is gender and c == century)
    return f"{province_code}{gc_digit}{yy:02d}{serial}"


__all__ = ["CCCDFormatError", "build_cccd", "parse_cccd"]
