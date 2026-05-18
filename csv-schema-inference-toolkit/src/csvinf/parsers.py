"""Type-detection parsers.

Each ``try_*`` function takes a raw string and returns ``None`` on a
failed parse, or the parsed value on success. Functions are
**strict**: a leading/trailing space, an internal alpha, or any
sentinel that can't unambiguously round-trip → ``None``.

Locale conventions handled:

* **VN-style decimal** ``"1.234.567,89"`` — period as thousands
  separator, comma as decimal point. Also recognised: ``"1234567,89"``
  and bare ``"1234567.89"``.
* **VN-style date** ``"17/05/2026"`` (dd/MM/yyyy) — common on
  receipts, invoices, government forms.
* **ISO date** ``"2026-05-17"`` and **ISO datetime**
  ``"2026-05-17T09:00:00"`` (with optional ``Z`` or ``+07:00``).
* **Boolean** — ``true``/``false``/``yes``/``no``/``1``/``0``,
  also Vietnamese ``Có`` / ``Không``.

The parser tries types in order: BOOL → INT → DATE → DATETIME →
DECIMAL → FLOAT → STRING (the fallback).
"""

from __future__ import annotations

import re
from datetime import date, datetime

_TRUE_TOKENS = frozenset(
    {
        "true",
        "t",
        "yes",
        "y",
        "1",
        "có",
        "co",
    }
)
_FALSE_TOKENS = frozenset(
    {
        "false",
        "f",
        "no",
        "n",
        "0",
        "không",
        "khong",
    }
)

# DD/MM/YYYY or DD-MM-YYYY (VN style)
_VN_DATE_RE = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$")
# YYYY-MM-DD or YYYY/MM/DD (ISO-ish)
_ISO_DATE_RE = re.compile(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$")
# Datetime: ISO with T or space separator
_ISO_DATETIME_RE = re.compile(
    r"^(\d{4})-(\d{1,2})-(\d{1,2})[T ](\d{1,2}):(\d{2})(?::(\d{2}))?"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
)

# Integer: optional sign, plain digits, optional thousands separators
_INT_RE = re.compile(r"^-?\d+$")
_INT_VN_RE = re.compile(r"^-?\d{1,3}(\.\d{3})+$")  # 1.234.567 (VN thousands)
_INT_EN_RE = re.compile(r"^-?\d{1,3}(,\d{3})+$")  # 1,234,567 (EN thousands)

# Decimal/float
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
_FLOAT_NEG_EXP_RE = re.compile(r"^-?\d+(\.\d+)?[eE][+-]?\d+$")
_VN_DECIMAL_RE = re.compile(r"^-?(\d{1,3}(\.\d{3})+|\d+),\d+$")  # 1.234.567,89
_DECIMAL_COMMA_RE = re.compile(r"^-?\d+,\d+$")  # 1234,89

# Currency / unit suffixes occasionally seen — we DO NOT auto-strip.
# An invoice column with "1.500.000 VND" rows is STRING, not numeric.


def try_bool(raw: str) -> bool | None:
    """Try parsing ``raw`` as a boolean. Returns ``None`` on failure."""
    if not raw:
        return None
    lower = raw.strip().lower()
    if lower in _TRUE_TOKENS:
        return True
    if lower in _FALSE_TOKENS:
        return False
    return None


def try_int(raw: str) -> int | None:
    """Try parsing ``raw`` as a signed integer.

    Accepts plain digits and VN/EN thousands separators.
    Rejects values that have any decimal point (those are FLOAT).
    """
    if not raw:
        return None
    s = raw.strip()
    if _INT_RE.match(s):
        return int(s)
    if _INT_VN_RE.match(s):
        return int(s.replace(".", ""))
    if _INT_EN_RE.match(s):
        return int(s.replace(",", ""))
    return None


def try_float(raw: str) -> float | None:
    """Try parsing ``raw`` as a float (EN locale: ``.`` decimal).

    Rejects values containing only digits (those are INT) and
    VN-style decimal (those route through ``try_decimal``).
    """
    if not raw:
        return None
    s = raw.strip()
    if _FLOAT_RE.match(s) or _FLOAT_NEG_EXP_RE.match(s):
        return float(s)
    return None


def try_decimal(raw: str) -> str | None:
    """Try parsing ``raw`` as a VN-locale decimal.

    Returns the **normalised string** (``"1234567.89"``) so the
    caller can round-trip exactly without float drift. Comma is
    the decimal point in VN locale.
    """
    if not raw:
        return None
    s = raw.strip()
    if _VN_DECIMAL_RE.match(s):
        # Replace thousands period with nothing, then comma with period.
        return s.replace(".", "").replace(",", ".")
    if _DECIMAL_COMMA_RE.match(s):
        return s.replace(",", ".")
    return None


def try_date(raw: str) -> date | None:
    """Try parsing ``raw`` as a date (VN dd/MM/yyyy or ISO yyyy-mm-dd)."""
    if not raw:
        return None
    s = raw.strip()
    m = _VN_DATE_RE.match(s)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        return _safe_date(y, mo, d)
    m = _ISO_DATE_RE.match(s)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        return _safe_date(y, mo, d)
    return None


def try_datetime(raw: str) -> datetime | None:
    """Try parsing ``raw`` as an ISO-style datetime."""
    if not raw:
        return None
    s = raw.strip()
    if not _ISO_DATETIME_RE.match(s):
        return None
    # datetime.fromisoformat handles most variants since 3.11; we
    # normalise trailing 'Z' to '+00:00' for 3.10 compatibility.
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def detect_date_format(raw: str) -> str:
    """Return the canonical format-string for a recognised date.

    ``"dd/MM/yyyy"`` for VN dates, ``"yyyy-mm-dd"`` for ISO, or
    empty string if no match.
    """
    s = raw.strip()
    if _VN_DATE_RE.match(s):
        return "dd/MM/yyyy"
    if _ISO_DATE_RE.match(s):
        return "yyyy-mm-dd"
    return ""


def detect_datetime_format(raw: str) -> str:
    """Return canonical format-string for an ISO datetime, or ""."""
    s = raw.strip()
    if _ISO_DATETIME_RE.match(s):
        return "iso8601"
    return ""


def _safe_date(year: int, month: int, day: int) -> date | None:
    """Construct a ``date`` returning ``None`` on out-of-range parts."""
    try:
        return date(year, month, day)
    except ValueError:
        return None


__all__ = [
    "detect_date_format",
    "detect_datetime_format",
    "try_bool",
    "try_date",
    "try_datetime",
    "try_decimal",
    "try_float",
    "try_int",
]
