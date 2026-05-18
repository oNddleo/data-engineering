"""BHYT card number format + prefix decoding.

The card number is **15 characters** per VSS Decision 1351/QĐ-BHXH 2015:
**1 scheme letter + 1 priority digit (1-5) + 13 region/identifier digits**.

* The **first character** is the issuance scheme:
    - ``D`` — Doanh nghiệp (employer-paid, the most common scheme)
    - ``H`` — Học sinh / Sinh viên (students)
    - ``T`` — Trẻ em (children under 6)
    - ``C`` — Cận nghèo (near-poor households)
    - ``G`` — Gia đình (voluntary/family)
    - ``X`` — Xã hội bảo trợ (social-protection beneficiaries)
* The **second character** is the priority digit (1 — 5):
    - ``1`` — Diện ưu tiên 1 (children, ethnic minorities in poor zones)
    - ``2`` — Diện ưu tiên 2 (war veterans, revolution contributors)
    - ``3`` — Diện ưu tiên 3 (poor / near-poor)
    - ``4`` — Diện ưu tiên 4 (regular)
    - ``5`` — Diện ưu tiên 5 (voluntary)

The remaining 13 digits are a province code (2) + identifier (11).

This module:

* Validates format only (length + character-class). Real VSS card
  validation also checks the identifier against the GDT registry —
  not modelled here.
* Decodes the prefix into a typed :class:`PrefixInfo`.
* Maps the priority code → :class:`ExemptionCategory`.
"""

from __future__ import annotations

from dataclasses import dataclass

from bhyt.schema import ExemptionCategory

_SCHEME_NAMES = {
    "D": "Doanh nghiệp (employer-paid)",
    "H": "Học sinh / Sinh viên (student)",
    "T": "Trẻ em (child under 6)",
    "C": "Cận nghèo (near-poor)",
    "G": "Gia đình (voluntary)",
    "X": "Xã hội bảo trợ (social protection)",
}

_PRIORITY_CATEGORY = {
    "1": ExemptionCategory.UU_TIEN_1,
    "2": ExemptionCategory.UU_TIEN_2,
    "3": ExemptionCategory.UU_TIEN_3,
    "4": ExemptionCategory.UU_TIEN_4,
    "5": ExemptionCategory.UU_TIEN_5,
}


@dataclass(frozen=True, slots=True)
class PrefixInfo:
    """Decoded BHYT card prefix."""

    scheme_letter: str
    scheme_name: str
    priority_letter: str
    category: ExemptionCategory


def is_valid_format(card_number: str) -> bool:
    """Format-only check: 1 scheme letter + 1 priority digit + 13 digits.

    Doesn't hit VSS — real validation also checks the trailing 13 digits
    against the GDT-published registry.
    """
    if len(card_number) != 15:
        return False
    if not card_number[0].isalpha() or not card_number[0].isupper():
        return False
    if card_number[0] not in _SCHEME_NAMES:
        return False
    if card_number[1] not in _PRIORITY_CATEGORY:
        return False
    return card_number[2:].isdigit()


def decode_prefix(card_number: str) -> PrefixInfo:
    """Decode the 2-letter prefix. Raises if the format is invalid."""
    if not is_valid_format(card_number):
        raise ValueError(f"invalid card_number format: {card_number!r}")
    scheme = card_number[0]
    priority = card_number[1]
    return PrefixInfo(
        scheme_letter=scheme,
        scheme_name=_SCHEME_NAMES[scheme],
        priority_letter=priority,
        category=_PRIORITY_CATEGORY[priority],
    )


def normalise(raw: str) -> str:
    """Strip whitespace and force uppercase. Doesn't validate."""
    return "".join(c for c in raw.upper() if not c.isspace())


__all__ = [
    "PrefixInfo",
    "decode_prefix",
    "is_valid_format",
    "normalise",
]
