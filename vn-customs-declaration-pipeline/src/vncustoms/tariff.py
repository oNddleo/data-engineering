"""Tariff rate lookup (import duty + VAT).

VN customs charges three layers of tax on imports:

1. **Import duty** (``thuế nhập khẩu``) — MFN rate from the
   preferential or ordinary tariff schedule, varies by HS chapter.
2. **Special consumption tax** (``thuế tiêu thụ đặc biệt``) — only on
   a short list of goods (alcohol, tobacco, cars, fuel). Out of scope
   for this lightweight calculator.
3. **VAT** (``thuế GTGT``) — applied on (customs value + import duty).

We ship a **realistic but illustrative** rate table keyed by HS
chapter, not the full 20 000-line schedule. Real production work
should plug in the official ``Biểu thuế xuất nhập khẩu`` exported
yearly by the Ministry of Finance.

VAT rates per VN tax law:

* 0 % — exports.
* 5 % — essentials (food, medical equipment, water, fertilizer).
* 8 % — temporarily reduced (2024–2026) standard rate.
* 10 % — standard rate before/after reduction.
"""

from __future__ import annotations

# Map HS chapter → import duty rate (decimal fraction, e.g. 0.10 = 10%).
# Numbers chosen to be in the ballpark of VN's MFN preferential schedule
# but you should always check the official tariff book for production use.
_DUTY_BY_CHAPTER: dict[str, float] = {
    # 01–05: live animals, meat, fish, dairy — mostly 5–20%
    "01": 0.05,
    "02": 0.20,
    "03": 0.20,
    "04": 0.10,
    "05": 0.05,
    # 07–08: vegetables, fruit — 15%
    "07": 0.15,
    "08": 0.20,
    # 09: coffee, tea, spices — 15%
    "09": 0.15,
    # 10–14: grains, milling — 5%
    "10": 0.05,
    "11": 0.10,
    # 15: fats, oils — 5%
    "15": 0.05,
    # 17: sugar — 25%
    "17": 0.25,
    # 22: beverages incl. alcohol — 30%
    "22": 0.30,
    # 24: tobacco — 30%
    "24": 0.30,
    # 27: mineral fuels — 5%
    "27": 0.05,
    # 28–38: chemicals — 5%
    "28": 0.03,
    "29": 0.03,
    "30": 0.00,
    "31": 0.00,
    "32": 0.05,
    "33": 0.15,
    "34": 0.15,
    "35": 0.10,
    "36": 0.05,
    "37": 0.05,
    "38": 0.05,
    # 39: plastics — 10%
    "39": 0.10,
    # 40: rubber — 5%
    "40": 0.05,
    # 41–43: leather — 15%
    "42": 0.20,
    # 44: wood — 10%
    "44": 0.10,
    # 48: paper — 10%
    "48": 0.10,
    # 50–63: textiles & garments — 12%
    "50": 0.05,
    "51": 0.05,
    "52": 0.05,
    "53": 0.05,
    "54": 0.10,
    "55": 0.10,
    "56": 0.10,
    "57": 0.15,
    "58": 0.12,
    "59": 0.10,
    "60": 0.12,
    "61": 0.20,
    "62": 0.20,
    "63": 0.15,
    # 64: footwear — 25%
    "64": 0.25,
    # 69: ceramics — 20%
    "69": 0.20,
    # 70: glass — 10%
    "70": 0.10,
    # 71: precious metals — 5%
    "71": 0.05,
    # 72–83: metals — 10%
    "72": 0.03,
    "73": 0.10,
    "74": 0.05,
    "75": 0.05,
    "76": 0.10,
    "82": 0.10,
    "83": 0.10,
    # 84: machinery — 0–5% (mostly 0)
    "84": 0.03,
    # 85: electrical machinery, electronics — 0–10% (mostly 0)
    "85": 0.05,
    # 87: vehicles — high (50–70% for cars; we average to 30)
    "87": 0.30,
    # 90: optical, measuring — 5%
    "90": 0.05,
    # 94: furniture — 25%
    "94": 0.25,
    # 95: toys — 15%
    "95": 0.15,
    # 96: misc manufactured — 15%
    "96": 0.15,
}

# VAT rate table by HS chapter. Most chapters are 8% during the 2024–2026
# temporary reduction; a short list of essentials is 5%; gold and a few
# others are 0%.
_VAT_BY_CHAPTER: dict[str, float] = {
    "03": 0.05,  # fish
    "04": 0.05,  # dairy
    "07": 0.05,  # veg
    "08": 0.05,  # fruit
    "10": 0.05,  # grains
    "30": 0.05,  # pharmaceuticals
    "31": 0.05,  # fertilizers
    "71": 0.00,  # precious metals (gold bullion not VAT'd as goods)
}

_VAT_DEFAULT = 0.08  # current standard VN VAT rate (8% reduced).


def duty_rate_for(chapter: str) -> float:
    """Return MFN preferential import duty rate for an HS chapter.

    Unknown chapters return the most-common rate (10 %), which is a
    deliberate fallback — declarations with unknown HS chapters should
    still calculate something, even if approximate.
    """
    if not (chapter.isdigit() and len(chapter) == 2):
        raise ValueError(f"chapter must be 2 digits, got {chapter!r}")
    return _DUTY_BY_CHAPTER.get(chapter, 0.10)


def vat_rate_for(chapter: str) -> float:
    """Return VAT rate for an HS chapter."""
    if not (chapter.isdigit() and len(chapter) == 2):
        raise ValueError(f"chapter must be 2 digits, got {chapter!r}")
    return _VAT_BY_CHAPTER.get(chapter, _VAT_DEFAULT)


__all__ = ["duty_rate_for", "vat_rate_for"]
