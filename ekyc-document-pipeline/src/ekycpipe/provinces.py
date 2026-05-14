"""Mã tỉnh / thành phố — the 3-digit province codes embedded in every CCCD.

Sourced from Thông tư 07/2016/TT-BCA (and subsequent amendments).
Codes are zero-padded 3-digit numeric strings and range over the
non-contiguous set 001–096. The 2025 province-merger reform doesn't
change *historical* CCCD numbers, so the legacy code table is still
load-bearing for any CCCD issued before the merger; we ship it
verbatim.

Keep this file string-keyed — even though the codes are numeric,
leading zeros are significant ("001" ≠ "1").
"""

from __future__ import annotations

PROVINCE_CODES: dict[str, str] = {
    "001": "Hà Nội",
    "002": "Hà Giang",
    "004": "Cao Bằng",
    "006": "Bắc Kạn",
    "008": "Tuyên Quang",
    "010": "Lào Cai",
    "011": "Điện Biên",
    "012": "Lai Châu",
    "014": "Sơn La",
    "015": "Yên Bái",
    "017": "Hòa Bình",
    "019": "Thái Nguyên",
    "020": "Lạng Sơn",
    "022": "Quảng Ninh",
    "024": "Bắc Giang",
    "025": "Phú Thọ",
    "026": "Vĩnh Phúc",
    "027": "Bắc Ninh",
    "030": "Hải Dương",
    "031": "Hải Phòng",
    "033": "Hưng Yên",
    "034": "Thái Bình",
    "035": "Hà Nam",
    "036": "Nam Định",
    "037": "Ninh Bình",
    "038": "Thanh Hóa",
    "040": "Nghệ An",
    "042": "Hà Tĩnh",
    "044": "Quảng Bình",
    "045": "Quảng Trị",
    "046": "Thừa Thiên Huế",
    "048": "Đà Nẵng",
    "049": "Quảng Nam",
    "051": "Quảng Ngãi",
    "052": "Bình Định",
    "054": "Phú Yên",
    "056": "Khánh Hòa",
    "058": "Ninh Thuận",
    "060": "Bình Thuận",
    "062": "Kon Tum",
    "064": "Gia Lai",
    "066": "Đắk Lắk",
    "067": "Đắk Nông",
    "068": "Lâm Đồng",
    "070": "Bình Phước",
    "072": "Tây Ninh",
    "074": "Bình Dương",
    "075": "Đồng Nai",
    "077": "Bà Rịa - Vũng Tàu",
    "079": "TP. Hồ Chí Minh",
    "080": "Long An",
    "082": "Tiền Giang",
    "083": "Bến Tre",
    "084": "Trà Vinh",
    "086": "Vĩnh Long",
    "087": "Đồng Tháp",
    "089": "An Giang",
    "091": "Kiên Giang",
    "092": "Cần Thơ",
    "093": "Hậu Giang",
    "094": "Sóc Trăng",
    "095": "Bạc Liêu",
    "096": "Cà Mau",
}
"""Mapping ``"079" → "TP. Hồ Chí Minh"`` for all 63 pre-merger provinces."""


def province_name(code: str) -> str | None:
    """Return the canonical province name for ``code``; ``None`` if unknown."""
    return PROVINCE_CODES.get(code)


def is_valid_province_code(code: str) -> bool:
    """Return True iff ``code`` is a registered 3-digit province code."""
    return len(code) == 3 and code.isdigit() and code in PROVINCE_CODES


__all__ = ["PROVINCE_CODES", "is_valid_province_code", "province_name"]
