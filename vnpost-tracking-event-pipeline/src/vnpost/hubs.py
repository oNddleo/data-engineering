"""VN courier hub network.

A curated set of high-volume courier hubs used by the major VN
operators. Hub codes follow ``<CITY>-<NAME>`` convention:

* ``HCM-*`` — TP Hồ Chí Minh (warehouses + sort centres)
* ``HN-*``  — Hà Nội
* ``DN-*``  — Đà Nẵng (central VN gateway)
* ``HP-*``  — Hải Phòng (north-east port)
* ``CT-*``  — Cần Thơ (Mekong Delta gateway)

The 16 hubs listed here cover ~80% of inter-city e-commerce parcel
volume per published Viettel Post + GHN aggregates. Production
callers extend with regional satellite hubs as needed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Hub:
    """One courier hub."""

    code: str  # e.g. "HCM-TPN"
    name_vi: str  # "Tân Phú"
    name_en: str  # "Tan Phu"
    city: str  # "HCM"
    is_gateway: bool = False  # primary regional gateway (sorts to other cities)


_HUBS: tuple[Hub, ...] = (
    # HCM core
    Hub("HCM-TPN", "Kho Tân Phú", "Tan Phu Hub", "HCM", True),
    Hub("HCM-Q12", "Kho Quận 12", "District 12 Hub", "HCM", True),
    Hub("HCM-BC", "Kho Bình Chánh", "Binh Chanh Hub", "HCM"),
    Hub("HCM-TD", "Kho Thủ Đức", "Thu Duc Hub", "HCM"),
    Hub("HCM-CC", "Kho Củ Chi", "Cu Chi Hub", "HCM"),
    # HN core
    Hub("HN-CG", "Kho Cầu Giấy", "Cau Giay Hub", "HN", True),
    Hub("HN-HD", "Kho Hà Đông", "Ha Dong Hub", "HN", True),
    Hub("HN-LB", "Kho Long Biên", "Long Bien Hub", "HN"),
    Hub("HN-DA", "Kho Đông Anh", "Dong Anh Hub", "HN"),
    # Đà Nẵng
    Hub("DN-HC", "Kho Hải Châu", "Hai Chau Hub", "DN", True),
    Hub("DN-LC", "Kho Liên Chiểu", "Lien Chieu Hub", "DN"),
    # Hải Phòng
    Hub("HP-NG", "Kho Ngô Quyền", "Ngo Quyen Hub", "HP", True),
    Hub("HP-AD", "Kho An Dương", "An Duong Hub", "HP"),
    # Cần Thơ
    Hub("CT-NK", "Kho Ninh Kiều", "Ninh Kieu Hub", "CT", True),
    Hub("CT-CR", "Kho Cái Răng", "Cai Rang Hub", "CT"),
    # National sortation centre
    Hub("VN-NSC", "Trung tâm phân loại quốc gia", "National Sortation Center", "HN", True),
)


_BY_CODE: dict[str, Hub] = {h.code: h for h in _HUBS}


def all_hubs() -> tuple[Hub, ...]:
    """Immutable tuple of every bundled hub."""
    return _HUBS


def by_code(code: str) -> Hub | None:
    """Lookup a hub by code; ``None`` if missing."""
    return _BY_CODE.get(code)


def by_city(city: str) -> list[Hub]:
    """Return all hubs in a city (``HCM``, ``HN``, …)."""
    return [h for h in _HUBS if h.city == city]


def gateways() -> list[Hub]:
    """Return hubs that act as primary inter-city sort centres."""
    return [h for h in _HUBS if h.is_gateway]


__all__ = ["Hub", "all_hubs", "by_city", "by_code", "gateways"]
