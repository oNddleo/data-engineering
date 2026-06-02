"""Bundled VN administrative-unit directory.

Covers:

* **All 63 provinces** (5 centrally-managed cities + 58 provinces)
  per Resolution 1211/2016/UBTVQH13 and post-2008 reorganizations.
* **Central districts** of the 5 directly-managed cities — Hồ Chí
  Minh City (24), Hà Nội (12), Đà Nẵng (8), Hải Phòng (7), Cần
  Thơ (5) = 56 districts.
* **Sample wards** in HCM Q1, Q3, Bình Thạnh and HN Hoàn Kiếm, Ba
  Đình — enough for parser tests; production callers should extend
  the table with their own data source (typically the General
  Statistics Office's GSO admin-unit dump).

All names use canonical Vietnamese diacritics. The directory is
deliberately bundled (no I/O at import) so consumers get a working
parser out of the box.
"""

from __future__ import annotations

from vnaddr.schema import AdminLevel, AdminUnit

# ---------- 63 provinces (codes match ISO 3166-2:VN where possible) ---------

_PROVINCES_RAW: tuple[tuple[str, str, str], ...] = (
    # 5 centrally-managed cities first
    ("HCM", "Thành phố Hồ Chí Minh", "Ho Chi Minh City"),
    ("HN", "Thành phố Hà Nội", "Ha Noi"),
    ("DN", "Thành phố Đà Nẵng", "Da Nang"),
    ("HP", "Thành phố Hải Phòng", "Hai Phong"),
    ("CT", "Thành phố Cần Thơ", "Can Tho"),
    # 58 provinces (alphabetical by VN name)
    ("AG", "Tỉnh An Giang", "An Giang"),
    ("BV", "Tỉnh Bà Rịa - Vũng Tàu", "Ba Ria - Vung Tau"),
    ("BG", "Tỉnh Bắc Giang", "Bac Giang"),
    ("BK", "Tỉnh Bắc Kạn", "Bac Kan"),
    ("BL", "Tỉnh Bạc Liêu", "Bac Lieu"),
    ("BN", "Tỉnh Bắc Ninh", "Bac Ninh"),
    ("BT", "Tỉnh Bến Tre", "Ben Tre"),
    ("BD", "Tỉnh Bình Định", "Binh Dinh"),
    ("BPN", "Tỉnh Bình Dương", "Binh Duong"),
    ("BP", "Tỉnh Bình Phước", "Binh Phuoc"),
    ("BTH", "Tỉnh Bình Thuận", "Binh Thuan"),
    ("CM", "Tỉnh Cà Mau", "Ca Mau"),
    ("CB", "Tỉnh Cao Bằng", "Cao Bang"),
    ("DL", "Tỉnh Đắk Lắk", "Dak Lak"),
    ("DK", "Tỉnh Đắk Nông", "Dak Nong"),
    ("DB", "Tỉnh Điện Biên", "Dien Bien"),
    ("DON", "Tỉnh Đồng Nai", "Dong Nai"),
    ("DT", "Tỉnh Đồng Tháp", "Dong Thap"),
    ("GL", "Tỉnh Gia Lai", "Gia Lai"),
    ("HG", "Tỉnh Hà Giang", "Ha Giang"),
    ("HNM", "Tỉnh Hà Nam", "Ha Nam"),
    ("HT", "Tỉnh Hà Tĩnh", "Ha Tinh"),
    ("HD", "Tỉnh Hải Dương", "Hai Duong"),
    ("HGI", "Tỉnh Hậu Giang", "Hau Giang"),
    ("HB", "Tỉnh Hòa Bình", "Hoa Binh"),
    ("HY", "Tỉnh Hưng Yên", "Hung Yen"),
    ("KH", "Tỉnh Khánh Hòa", "Khanh Hoa"),
    ("KG", "Tỉnh Kiên Giang", "Kien Giang"),
    ("KT", "Tỉnh Kon Tum", "Kon Tum"),
    ("LC", "Tỉnh Lai Châu", "Lai Chau"),
    ("LD", "Tỉnh Lâm Đồng", "Lam Dong"),
    ("LSO", "Tỉnh Lạng Sơn", "Lang Son"),
    ("LCA", "Tỉnh Lào Cai", "Lao Cai"),
    ("LA", "Tỉnh Long An", "Long An"),
    ("ND", "Tỉnh Nam Định", "Nam Dinh"),
    ("NA", "Tỉnh Nghệ An", "Nghe An"),
    ("NB", "Tỉnh Ninh Bình", "Ninh Binh"),
    ("NT", "Tỉnh Ninh Thuận", "Ninh Thuan"),
    ("PT", "Tỉnh Phú Thọ", "Phu Tho"),
    ("PY", "Tỉnh Phú Yên", "Phu Yen"),
    ("QB", "Tỉnh Quảng Bình", "Quang Binh"),
    ("QNA", "Tỉnh Quảng Nam", "Quang Nam"),
    ("QNG", "Tỉnh Quảng Ngãi", "Quang Ngai"),
    ("QN", "Tỉnh Quảng Ninh", "Quang Ninh"),
    ("QT", "Tỉnh Quảng Trị", "Quang Tri"),
    ("ST", "Tỉnh Sóc Trăng", "Soc Trang"),
    ("SL", "Tỉnh Sơn La", "Son La"),
    ("TNH", "Tỉnh Tây Ninh", "Tay Ninh"),
    ("TB", "Tỉnh Thái Bình", "Thai Binh"),
    ("TN", "Tỉnh Thái Nguyên", "Thai Nguyen"),
    ("TH", "Tỉnh Thanh Hóa", "Thanh Hoa"),
    ("TTH", "Tỉnh Thừa Thiên Huế", "Thua Thien Hue"),
    ("TG", "Tỉnh Tiền Giang", "Tien Giang"),
    ("TV", "Tỉnh Trà Vinh", "Tra Vinh"),
    ("TQ", "Tỉnh Tuyên Quang", "Tuyen Quang"),
    ("VL", "Tỉnh Vĩnh Long", "Vinh Long"),
    ("VP", "Tỉnh Vĩnh Phúc", "Vinh Phuc"),
    ("YB", "Tỉnh Yên Bái", "Yen Bai"),
)


_HCM_DISTRICTS_RAW: tuple[tuple[str, str, str], ...] = (
    ("HCM:Q1", "Quận 1", "District 1"),
    ("HCM:Q3", "Quận 3", "District 3"),
    ("HCM:Q4", "Quận 4", "District 4"),
    ("HCM:Q5", "Quận 5", "District 5"),
    ("HCM:Q6", "Quận 6", "District 6"),
    ("HCM:Q7", "Quận 7", "District 7"),
    ("HCM:Q8", "Quận 8", "District 8"),
    ("HCM:Q10", "Quận 10", "District 10"),
    ("HCM:Q11", "Quận 11", "District 11"),
    ("HCM:Q12", "Quận 12", "District 12"),
    ("HCM:BT", "Quận Bình Thạnh", "Binh Thanh District"),
    ("HCM:GV", "Quận Gò Vấp", "Go Vap District"),
    ("HCM:PN", "Quận Phú Nhuận", "Phu Nhuan District"),
    ("HCM:TB", "Quận Tân Bình", "Tan Binh District"),
    ("HCM:TP", "Quận Tân Phú", "Tan Phu District"),
    ("HCM:BTN", "Quận Bình Tân", "Binh Tan District"),
    ("HCM:TD", "Thành phố Thủ Đức", "Thu Duc City"),
    ("HCM:BC", "Huyện Bình Chánh", "Binh Chanh District"),
    ("HCM:NB", "Huyện Nhà Bè", "Nha Be District"),
    ("HCM:CG", "Huyện Cần Giờ", "Can Gio District"),
    ("HCM:HM", "Huyện Hóc Môn", "Hoc Mon District"),
    ("HCM:CC", "Huyện Củ Chi", "Cu Chi District"),
)


_HN_DISTRICTS_RAW: tuple[tuple[str, str, str], ...] = (
    ("HN:HK", "Quận Hoàn Kiếm", "Hoan Kiem District"),
    ("HN:BD", "Quận Ba Đình", "Ba Dinh District"),
    ("HN:DD", "Quận Đống Đa", "Dong Da District"),
    ("HN:HBT", "Quận Hai Bà Trưng", "Hai Ba Trung District"),
    ("HN:CG", "Quận Cầu Giấy", "Cau Giay District"),
    ("HN:TX", "Quận Thanh Xuân", "Thanh Xuan District"),
    ("HN:NTL", "Quận Nam Từ Liêm", "Nam Tu Liem District"),
    ("HN:BTL", "Quận Bắc Từ Liêm", "Bac Tu Liem District"),
    ("HN:LB", "Quận Long Biên", "Long Bien District"),
    ("HN:HD", "Quận Hà Đông", "Ha Dong District"),
    ("HN:HMA", "Quận Hoàng Mai", "Hoang Mai District"),
    ("HN:TH", "Quận Tây Hồ", "Tay Ho District"),
)


_DN_DISTRICTS_RAW: tuple[tuple[str, str, str], ...] = (
    ("DN:HC", "Quận Hải Châu", "Hai Chau District"),
    ("DN:TK", "Quận Thanh Khê", "Thanh Khe District"),
    ("DN:ST", "Quận Sơn Trà", "Son Tra District"),
    ("DN:NHS", "Quận Ngũ Hành Sơn", "Ngu Hanh Son District"),
    ("DN:LC", "Quận Liên Chiểu", "Lien Chieu District"),
    ("DN:CL", "Quận Cẩm Lệ", "Cam Le District"),
)


# Sample wards — illustrative, not exhaustive. Production callers
# should extend with the full GSO directory.
_WARDS_RAW: tuple[tuple[str, str, str], ...] = (
    # HCM Quận 1
    ("HCM:Q1:BNG", "Phường Bến Nghé", "Ben Nghe Ward"),
    ("HCM:Q1:BT", "Phường Bến Thành", "Ben Thanh Ward"),
    ("HCM:Q1:CK", "Phường Cầu Kho", "Cau Kho Ward"),
    ("HCM:Q1:DK", "Phường Đa Kao", "Da Kao Ward"),
    ("HCM:Q1:NCT", "Phường Nguyễn Cư Trinh", "Nguyen Cu Trinh Ward"),
    # HCM Quận 3
    ("HCM:Q3:VP1", "Phường Võ Thị Sáu", "Vo Thi Sau Ward"),
    ("HCM:Q3:1", "Phường 1", "Ward 1"),
    ("HCM:Q3:2", "Phường 2", "Ward 2"),
    # HCM Bình Thạnh
    ("HCM:BT:25", "Phường 25", "Ward 25"),
    ("HCM:BT:26", "Phường 26", "Ward 26"),
    # HN Hoàn Kiếm
    ("HN:HK:HB", "Phường Hàng Bài", "Hang Bai Ward"),
    ("HN:HK:HBOM", "Phường Hàng Bồ", "Hang Bo Ward"),
    ("HN:HK:LL", "Phường Lý Thái Tổ", "Ly Thai To Ward"),
    # HN Ba Đình
    ("HN:BD:KM", "Phường Kim Mã", "Kim Ma Ward"),
    ("HN:BD:DK", "Phường Điện Biên", "Dien Bien Ward"),
)


def _build_units() -> tuple[AdminUnit, ...]:
    """Materialise the immutable directory at import."""
    out: list[AdminUnit] = []
    for code, name_vi, name_en in _PROVINCES_RAW:
        out.append(
            AdminUnit(
                code=code,
                name_vi=name_vi,
                name_en=name_en,
                level=AdminLevel.PROVINCE,
            )
        )
    for code, name_vi, name_en in _HCM_DISTRICTS_RAW:
        out.append(
            AdminUnit(
                code=code,
                name_vi=name_vi,
                name_en=name_en,
                level=AdminLevel.DISTRICT,
                parent_code="HCM",
            )
        )
    for code, name_vi, name_en in _HN_DISTRICTS_RAW:
        out.append(
            AdminUnit(
                code=code,
                name_vi=name_vi,
                name_en=name_en,
                level=AdminLevel.DISTRICT,
                parent_code="HN",
            )
        )
    for code, name_vi, name_en in _DN_DISTRICTS_RAW:
        out.append(
            AdminUnit(
                code=code,
                name_vi=name_vi,
                name_en=name_en,
                level=AdminLevel.DISTRICT,
                parent_code="DN",
            )
        )
    for code, name_vi, name_en in _WARDS_RAW:
        parent_code = ":".join(code.split(":")[:2])
        out.append(
            AdminUnit(
                code=code,
                name_vi=name_vi,
                name_en=name_en,
                level=AdminLevel.WARD,
                parent_code=parent_code,
            )
        )
    return tuple(out)


_ALL_UNITS: tuple[AdminUnit, ...] = _build_units()
_BY_CODE: dict[str, AdminUnit] = {u.code: u for u in _ALL_UNITS}


def all_units() -> tuple[AdminUnit, ...]:
    """Immutable tuple of every bundled administrative unit."""
    return _ALL_UNITS


def by_level(level: AdminLevel) -> list[AdminUnit]:
    """Return all units at the given level."""
    return [u for u in _ALL_UNITS if u.level is level]


def by_code(code: str) -> AdminUnit | None:
    """Look up a unit by its full code; ``None`` if missing."""
    return _BY_CODE.get(code)


def by_parent(parent_code: str) -> list[AdminUnit]:
    """Return units whose ``parent_code`` matches the given code."""
    return [u for u in _ALL_UNITS if u.parent_code == parent_code]


def n_provinces() -> int:
    """Number of bundled provinces (should be 63)."""
    return len(by_level(AdminLevel.PROVINCE))


__all__ = [
    "all_units",
    "by_code",
    "by_level",
    "by_parent",
    "n_provinces",
]
