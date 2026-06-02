"""Vietnamese district directory — HCM, Hà Nội, Đà Nẵng cores.

District codes follow the convention ``"<CITY>:<DISTRICT>"``:

* ``HCM`` — Hồ Chí Minh City (TP HCM)
* ``HN``  — Hà Nội
* ``DN``  — Đà Nẵng

District codes within each city are the official short abbreviations
used in administrative records (Q1 = Quận 1, HK = Hoàn Kiếm, etc).

Only the high-volume central districts are bundled — they cover
~80% of ride-share demand per published Grab VN aggregates.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class District:
    """One district entry."""

    code: str  # full code, e.g. "HCM:Q1"
    city: str  # "HCM", "HN", "DN"
    name_vi: str  # "Quận 1"
    name_en: str  # "District 1"


_DISTRICTS: tuple[District, ...] = (
    # HCMC central
    District("HCM:Q1", "HCM", "Quận 1", "District 1"),
    District("HCM:Q3", "HCM", "Quận 3", "District 3"),
    District("HCM:Q4", "HCM", "Quận 4", "District 4"),
    District("HCM:Q5", "HCM", "Quận 5", "District 5"),
    District("HCM:Q7", "HCM", "Quận 7", "District 7"),
    District("HCM:Q10", "HCM", "Quận 10", "District 10"),
    District("HCM:BT", "HCM", "Quận Bình Thạnh", "Binh Thanh District"),
    District("HCM:GV", "HCM", "Quận Gò Vấp", "Go Vap District"),
    District("HCM:PN", "HCM", "Quận Phú Nhuận", "Phu Nhuan District"),
    District("HCM:TD", "HCM", "Thành phố Thủ Đức", "Thu Duc City"),
    # Hà Nội central
    District("HN:HK", "HN", "Quận Hoàn Kiếm", "Hoan Kiem District"),
    District("HN:BD", "HN", "Quận Ba Đình", "Ba Dinh District"),
    District("HN:DD", "HN", "Quận Đống Đa", "Dong Da District"),
    District("HN:HBT", "HN", "Quận Hai Bà Trưng", "Hai Ba Trung District"),
    District("HN:CG", "HN", "Quận Cầu Giấy", "Cau Giay District"),
    District("HN:TX", "HN", "Quận Thanh Xuân", "Thanh Xuan District"),
    District("HN:NTL", "HN", "Quận Nam Từ Liêm", "Nam Tu Liem District"),
    # Đà Nẵng central
    District("DN:HC", "DN", "Quận Hải Châu", "Hai Chau District"),
    District("DN:TK", "DN", "Quận Thanh Khê", "Thanh Khe District"),
    District("DN:ST", "DN", "Quận Sơn Trà", "Son Tra District"),
)

_BY_CODE: dict[str, District] = {d.code: d for d in _DISTRICTS}


def lookup(code: str) -> District | None:
    """Return the district entry for ``code`` or ``None`` if unknown."""
    return _BY_CODE.get(code)


def is_valid(code: str) -> bool:
    """``True`` if ``code`` is a recognised district."""
    return code in _BY_CODE


def by_city(city: str) -> list[District]:
    """Return all districts in ``city`` (HCM / HN / DN)."""
    return [d for d in _DISTRICTS if d.city == city]


def all_codes() -> list[str]:
    """Every registered district code, alphabetically sorted."""
    return sorted(_BY_CODE)


__all__ = ["District", "all_codes", "by_city", "is_valid", "lookup"]
