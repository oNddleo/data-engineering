"""Area parser — extract m² from free text.

Surface forms we handle:

* ``"75 m2"`` → 75
* ``"75m²"`` → 75
* ``"75.5m²"`` → 76 (rounded up)
* ``"75,5 m2"`` → 76
* ``"7x10m"`` → 70 (frontage × depth)
* ``"diện tích 80m2"`` → 80
"""

from __future__ import annotations

import re

_AREA_RE = re.compile(
    r"(?P<dim1>\d+(?:[.,]\d+)?)\s*[x×]\s*(?P<dim2>\d+(?:[.,]\d+)?)\s*m"
    r"|"
    r"(?P<single>\d+(?:[.,]\d+)?)\s*m(?:²|2)?",
    re.IGNORECASE,
)


def parse_area_m2(text: str) -> int:
    """Parse an area string and return whole m² (rounded up)."""
    if not text:
        raise ValueError("text must be non-empty")
    m = _AREA_RE.search(text.lower())
    if m is None:
        raise ValueError(f"could not parse area from {text!r}")
    if m.group("single"):
        n = _to_float(m.group("single"))
    else:
        d1 = _to_float(m.group("dim1"))
        d2 = _to_float(m.group("dim2"))
        n = d1 * d2
    if n <= 0:
        raise ValueError(f"area must be > 0, got {n}")
    return int(n + 0.999)  # ceil


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


__all__ = ["parse_area_m2"]
