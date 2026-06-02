"""Seeded synthetic VN address generator.

Produces realistic-looking addresses across four "noise levels":

* **CLEAN** — full diacritics, full names, comma-separated.
* **ABBREV** — common abbreviations: ``Q.1``, ``P. Bến Nghé``, ``TP. HCM``.
* **FOLDED** — diacritics dropped (common when typed on a non-VN keyboard).
* **TYPO** — 1-2 char typos sprinkled in to exercise fuzzy matching.

Useful for smoke tests + benchmarking parser robustness.
"""

from __future__ import annotations

import random
from enum import Enum

from vnaddr.normalize import fold_diacritics
from vnaddr.schema import AdminLevel
from vnaddr.units import by_level, by_parent


class NoiseLevel(str, Enum):
    """How dirty the simulator should make its output."""

    CLEAN = "CLEAN"
    ABBREV = "ABBREV"
    FOLDED = "FOLDED"
    TYPO = "TYPO"


_STREETS = (
    "Lê Lợi",
    "Nguyễn Huệ",
    "Đồng Khởi",
    "Pasteur",
    "Nam Kỳ Khởi Nghĩa",
    "Trần Hưng Đạo",
    "Hai Bà Trưng",
    "Lý Tự Trọng",
    "Lê Thánh Tôn",
    "Cách Mạng Tháng Tám",
    "Võ Văn Tần",
    "Tôn Đức Thắng",
)


def generate(
    *,
    n: int = 100,
    noise: NoiseLevel = NoiseLevel.CLEAN,
    seed: int = 0,
) -> list[str]:
    """Generate ``n`` synthetic addresses with the chosen noise level."""
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    rng = random.Random(seed)

    # Build a flat list of (ward_name, district_name, province_name) triples.
    triples: list[tuple[str, str, str]] = []
    for province_unit in by_level(AdminLevel.PROVINCE):
        for district_unit in by_parent(province_unit.code):
            for ward_unit in by_parent(district_unit.code):
                triples.append(
                    (ward_unit.name_vi, district_unit.name_vi, province_unit.name_vi),
                )
    if not triples:
        return []

    out: list[str] = []
    for _ in range(n):
        ward_name, district_name, province_name = rng.choice(triples)
        street_number = rng.randint(1, 999)
        street = rng.choice(_STREETS)
        clean = f"{street_number} {street}, {ward_name}, {district_name}, {province_name}"
        if noise is NoiseLevel.CLEAN:
            out.append(clean)
        elif noise is NoiseLevel.ABBREV:
            out.append(_apply_abbrev(clean))
        elif noise is NoiseLevel.FOLDED:
            out.append(fold_diacritics(clean))
        elif noise is NoiseLevel.TYPO:
            out.append(_apply_typo(clean, rng))
        else:
            raise ValueError(f"unknown noise level: {noise}")
    return out


def _apply_abbrev(text: str) -> str:
    """Inject common VN address abbreviations."""
    out = text
    out = out.replace("Thành phố Hồ Chí Minh", "TP.HCM")
    out = out.replace("Thành phố Hà Nội", "Hà Nội")
    out = out.replace("Thành phố Đà Nẵng", "Đà Nẵng")
    # Replace "Quận N" → "Q.N"
    import re

    out = re.sub(r"Quận (\d+)", r"Q.\1", out)
    # Replace "Phường " → "P. "
    out = out.replace("Phường ", "P. ")
    return out


def _apply_typo(text: str, rng: random.Random) -> str:
    """Introduce 1-2 single-character typos."""
    chars = list(text)
    n_typos = rng.randint(1, 2)
    for _ in range(n_typos):
        if not chars:
            break
        idx = rng.randint(0, len(chars) - 1)
        ch = chars[idx]
        if not ch.isalpha():
            continue
        # Swap with a random adjacent letter.
        chars[idx] = rng.choice("abcdefghiklmnoprstuvxy")
    return "".join(chars)


__all__ = ["NoiseLevel", "generate"]
