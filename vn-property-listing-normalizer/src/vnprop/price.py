"""VN price parser — handles ``tỷ``, ``triệu``, ``nghìn``, and raw VND.

Common surface forms in real-estate listings:

* ``"2.5 tỷ"`` → 2_500_000_000 VND
* ``"850 triệu"`` → 850_000_000 VND
* ``"3,2 tỷ"`` → 3_200_000_000 VND (comma decimal, VN locale)
* ``"5.500.000.000"`` → 5_500_000_000 VND (dot-grouped thousands)
* ``"50tr/m²"`` → 50_000_000 VND/m² (compact abbreviation)

We parse the *amount portion only*; per-m² calculations are handled
upstream by ``schema.Listing.price_per_m2_vnd``.
"""

from __future__ import annotations

import re

# Order matters: longer unit names first so "tỷ" doesn't shadow "tr".
_UNIT_TABLE: tuple[tuple[str, int], ...] = (
    ("tỷ", 1_000_000_000),
    ("ty", 1_000_000_000),  # ASCII-stripped variant
    ("triệu", 1_000_000),
    ("trieu", 1_000_000),
    ("tr", 1_000_000),
    ("nghìn", 1_000),
    ("nghin", 1_000),
    ("k", 1_000),
    ("vnd", 1),
    ("đ", 1),
)

_NUMBER_RE = re.compile(r"^([\d.,]+)\s*(.*)$")


def parse_price_vnd(text: str) -> int:
    """Parse a VN-style price string into an integer VND amount."""
    if not text:
        raise ValueError("text must be non-empty")
    s = text.strip().lower()
    s = s.replace(" ", "").replace("/m²", "").replace("/m2", "")
    m = _NUMBER_RE.match(s)
    if m is None:
        raise ValueError(f"could not parse price from {text!r}")
    num_str, unit = m.group(1), m.group(2)
    multiplier = 1  # default: raw VND
    for token, mult in _UNIT_TABLE:
        if unit.startswith(token):
            multiplier = mult
            break
    # Normalise the number: VN uses both "," and "." as decimal or thousand
    # sep. Heuristic: if both appear, "." groups thousands and "," is decimal.
    # If only "." appears and the segment after it is exactly 3 digits, treat
    # as a thousands grouping; otherwise treat as decimal.
    n = _parse_number(num_str)
    return int(n * multiplier)


def _parse_number(s: str) -> float:
    """Parse a VN-locale number where ``,`` is the decimal separator."""
    has_comma = "," in s
    has_dot = "." in s
    if has_comma and has_dot:
        # "1.234,5" — dots are thousands, comma is decimal.
        s = s.replace(".", "").replace(",", ".")
    elif has_comma:
        # "2,5" → "2.5"
        s = s.replace(",", ".")
    elif has_dot:
        # If the trailing segment is exactly 3 digits, dots are thousands.
        parts = s.split(".")
        if all(len(p) == 3 for p in parts[1:]):
            s = s.replace(".", "")
        # else treat as decimal as-is ("2.5")
    try:
        return float(s)
    except ValueError as exc:
        raise ValueError(f"invalid number {s!r}") from exc


def format_price_vnd(value_vnd: int) -> str:
    """Format an integer VND amount as the most-readable VN unit."""
    if value_vnd < 0:
        raise ValueError("value_vnd must be >= 0")
    if value_vnd >= 1_000_000_000:
        n = value_vnd / 1_000_000_000
        return f"{n:.2f} tỷ"
    if value_vnd >= 1_000_000:
        n = value_vnd / 1_000_000
        return f"{n:.0f} triệu"
    return f"{value_vnd:,} VND"


__all__ = ["format_price_vnd", "parse_price_vnd"]
