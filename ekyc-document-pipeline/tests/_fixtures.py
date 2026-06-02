"""Shared test fixtures + factories."""

from __future__ import annotations

from datetime import date
from typing import Any

from ekycpipe.bca import BCARecord
from ekycpipe.cccd import build_cccd
from ekycpipe.schema import CitizenRecord, Gender, OCRResult

# Sentinel — lets factories distinguish "caller passed None on purpose"
# from "caller didn't pass anything, use the default".
_UNSET: Any = object()


def hcm_male_1995_serial(serial: str = "012345") -> str:
    """Build a deterministic HCM-province, male-1995 CCCD."""
    return build_cccd(
        province_code="079",  # TP. Hồ Chí Minh
        gender=Gender.MALE,
        birth_year=1995,
        serial=serial,
    )


def hn_female_2002_serial(serial: str = "654321") -> str:
    """Build a deterministic Hà-Nội, female-2002 CCCD."""
    return build_cccd(
        province_code="001",  # Hà Nội
        gender=Gender.FEMALE,
        birth_year=2002,
        serial=serial,
    )


def make_citizen(
    *,
    cccd: Any = _UNSET,
    full_name: str = "Nguyễn Văn A",
    date_of_birth: date | None = None,
    gender: Gender = Gender.MALE,
    hometown_province_code: str = "079",
    place_of_residence: str = "123 Lê Lợi, P. Bến Nghé, Q.1, TP.HCM",
    issued_at: date | None = None,
    expires_at: date | None = None,
) -> CitizenRecord:
    return CitizenRecord(
        cccd=hcm_male_1995_serial() if cccd is _UNSET else cccd,
        full_name=full_name,
        date_of_birth=date_of_birth or date(1995, 5, 15),
        gender=gender,
        hometown_province_code=hometown_province_code,
        place_of_residence=place_of_residence,
        issued_at=issued_at or date(2023, 1, 15),
        expires_at=expires_at,
    )


def make_ocr(
    *,
    cccd: Any = _UNSET,
    full_name: str | None = "Nguyễn Văn A",
    date_of_birth: str | None = "15/05/1995",
    gender: str | None = "Nam",
    hometown: str | None = "TP. Hồ Chí Minh",
    place_of_residence: str | None = "123 Lê Lợi, P. Bến Nghé, Q.1, TP.HCM",
    issued_at: str | None = "15/01/2023",
    expires_at: str | None = "15/01/2033",
    confidence: float | None = 0.95,
) -> OCRResult:
    return OCRResult(
        cccd=hcm_male_1995_serial() if cccd is _UNSET else cccd,
        full_name=full_name,
        date_of_birth=date_of_birth,
        gender=gender,
        hometown=hometown,
        place_of_residence=place_of_residence,
        issued_at=issued_at,
        expires_at=expires_at,
        confidence=confidence,
    )


def make_bca(
    *,
    cccd: str | None = None,
    full_name: str = "Nguyễn Văn A",
    date_of_birth: date | None = None,
    gender: Gender = Gender.MALE,
    hometown_province_code: str = "079",
) -> BCARecord:
    return BCARecord(
        cccd=cccd or hcm_male_1995_serial(),
        full_name=full_name,
        date_of_birth=date_of_birth or date(1995, 5, 15),
        gender=gender,
        hometown_province_code=hometown_province_code,
    )


__all__ = [
    "hcm_male_1995_serial",
    "hn_female_2002_serial",
    "make_bca",
    "make_citizen",
    "make_ocr",
]
