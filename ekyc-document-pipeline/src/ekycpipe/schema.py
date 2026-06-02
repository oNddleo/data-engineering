"""Schema for the eKYC pipeline.

The four shapes that flow through the system:

* **OCRResult** — raw fields recognised from a CCCD image. All
  strings are *as printed on the card* (might be UPPER-CASE, might
  have OCR noise).
* **CCCDFields** — what we get from *parsing* the 12-digit number
  itself (province + gender + birth century + birth year + serial).
  Independent of OCR — derivable from the number alone.
* **CitizenRecord** — the canonical, structured-typed plaintext
  view used by the pipeline before encryption.
* **Gender** — the enum the rest of the codebase uses.

We keep CCCDFields separate from CitizenRecord because the *number*
already encodes some of the citizen's data (province, gender,
birth year), and we want to validate that those embedded fields
agree with what the OCR reported. If the OCR'd birth year is 1990
but the CCCD encodes 1995, that's a fraud signal regardless of
what BCA says.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class Gender(str, Enum):
    """Binary gender as encoded on a CCCD."""

    MALE = "MALE"
    FEMALE = "FEMALE"


@dataclass(frozen=True, slots=True)
class CCCDFields:
    """The four components encoded in the 12-digit CCCD number itself."""

    province_code: str  # 3-digit
    gender: Gender
    century: int  # 19, 20, 21, 22, 23
    birth_year_yy: int  # 0–99 (last two digits)
    serial: str  # 6-digit

    @property
    def birth_year(self) -> int:
        return self.century * 100 + self.birth_year_yy


@dataclass(frozen=True, slots=True)
class OCRResult:
    """Raw OCR output — string fields as recognised from the card image."""

    cccd: str | None
    full_name: str | None
    date_of_birth: str | None  # raw text — caller parses
    gender: str | None  # "Nam" / "Nữ" or normalised
    hometown: str | None
    place_of_residence: str | None
    issued_at: str | None
    expires_at: str | None
    confidence: float | None = None  # OCR engine self-reported

    @property
    def is_complete(self) -> bool:
        """True iff every required field has been recognised."""
        return all(
            v is not None and v.strip()
            for v in (self.cccd, self.full_name, self.date_of_birth, self.gender)
        )


@dataclass(frozen=True, slots=True)
class CitizenRecord:
    """Structured, parsed plaintext view of a citizen — pre-encryption."""

    cccd: str
    full_name: str
    date_of_birth: date
    gender: Gender
    hometown_province_code: str
    place_of_residence: str
    issued_at: date
    expires_at: date | None = None  # None == permanent

    def __post_init__(self) -> None:
        if not self.cccd:
            raise ValueError("cccd must be non-empty")
        if not self.full_name.strip():
            raise ValueError("full_name must be non-empty")
        if not self.hometown_province_code:
            raise ValueError("hometown_province_code must be non-empty")
        if self.expires_at is not None and self.expires_at < self.issued_at:
            raise ValueError("expires_at cannot be before issued_at")


__all__ = ["CCCDFields", "CitizenRecord", "Gender", "OCRResult"]
