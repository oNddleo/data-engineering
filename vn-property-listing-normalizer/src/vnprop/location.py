"""Province / district / ward extractor (light — keyword-based).

VN administrative hierarchy: Tỉnh / Thành phố → Quận / Huyện → Phường / Xã.

We don't try to enumerate every province/district. We extract whatever
the text labels with the usual VN prefixes (Quận, Huyện, Phường, Xã,
TP., Thành phố, Tỉnh) and return what we find. For a full directory,
see the companion ``vn-address-parser`` build.
"""

from __future__ import annotations

import re

# Province / district / ward patterns. Non-greedy names that terminate
# at any of: comma, period, newline, end-of-string, or the start of the
# next-level admin keyword.
_PROVINCE_PATTERNS = (
    re.compile(r"\bTP\.?\s+(?P<name>[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ ]+?)(?=[,.\n]|$)"),
    re.compile(r"\bTỉnh\s+(?P<name>[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ ]+?)(?=[,.\n]|$)"),
    re.compile(r"\bThành\s+phố\s+(?P<name>[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ ]+?)(?=[,.\n]|$)"),
)
_DISTRICT_PATTERNS = (
    re.compile(r"\bQuận\s+(?P<name>\d+|[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ ]+?)(?=[,.\n]|$|\s+TP|\s+Tỉnh)"),
    re.compile(r"\bQ\.\s*(?P<name>\d+|[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ ]+?)(?=[,.\n]|$|\s+TP|\s+Tỉnh)"),
    re.compile(r"\bHuyện\s+(?P<name>[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ ]+?)(?=[,.\n]|$|\s+TP|\s+Tỉnh)"),
)
_WARD_PATTERNS = (
    re.compile(
        r"\bPhường\s+(?P<name>\d+|[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ ]+?)(?=[,.\n]|$|\s+Quận|\s+Q\.)"
    ),
    re.compile(r"\bP\.\s*(?P<name>\d+|[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ ]+?)(?=[,.\n]|$|\s+Quận|\s+Q\.)"),
    re.compile(r"\bXã\s+(?P<name>[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ ]+?)(?=[,.\n]|$|\s+Huyện)"),
)


def parse_province(text: str) -> str:
    """Return the most likely province name, or ``""`` if none found."""
    for pat in _PROVINCE_PATTERNS:
        m = pat.search(text)
        if m:
            return _label("TP.", m.group("name").strip())
    return ""


def parse_district(text: str) -> str:
    for pat in _DISTRICT_PATTERNS:
        m = pat.search(text)
        if m:
            name = m.group("name").strip()
            return f"Quận {name}" if name.isdigit() else _label("Quận", name)
    return ""


def parse_ward(text: str) -> str:
    for pat in _WARD_PATTERNS:
        m = pat.search(text)
        if m:
            name = m.group("name").strip()
            return f"Phường {name}" if name.isdigit() else _label("Phường", name)
    return ""


def _label(prefix: str, name: str) -> str:
    """Attach the canonical prefix if not already present."""
    name = name.strip()
    if not name:
        return ""
    return f"{prefix} {name}" if prefix.lower() not in name.lower() else name


__all__ = ["parse_district", "parse_province", "parse_ward"]
