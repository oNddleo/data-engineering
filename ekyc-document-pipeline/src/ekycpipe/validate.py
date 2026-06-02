"""Validation rules — wrap each rule's pass/fail/warn behaviour cleanly."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING

from ekycpipe.cccd import CCCDFormatError, parse_cccd
from ekycpipe.schema import Gender

if TYPE_CHECKING:
    from ekycpipe.bca import BCADatabase, BCARecord
    from ekycpipe.schema import OCRResult


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """One step's verdict — pass/fail + reason trail."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _ok() -> ValidationResult:
    return ValidationResult(is_valid=True)


def _fail(*errors: str) -> ValidationResult:
    return ValidationResult(is_valid=False, errors=tuple(errors))


def _warn(*warnings: str) -> ValidationResult:
    return ValidationResult(is_valid=True, warnings=tuple(warnings))


# ---------------------------------------------------------------------------
# Helpers


_GENDER_TEXT_VN: dict[str, Gender] = {
    "nam": Gender.MALE,
    "male": Gender.MALE,
    "m": Gender.MALE,
    "nữ": Gender.FEMALE,
    "nu": Gender.FEMALE,
    "female": Gender.FEMALE,
    "f": Gender.FEMALE,
}


def parse_gender_text(raw: str) -> Gender | None:
    """Best-effort gender parser — accepts 'Nam', 'Nữ', 'Male', 'Female', etc."""
    return _GENDER_TEXT_VN.get(raw.strip().lower())


def parse_date_dmy(raw: str) -> date | None:
    """Parse ``dd/mm/yyyy`` (the format printed on a CCCD). Return ``None`` on failure."""
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Individual rules


def validate_cccd_format(cccd: str) -> ValidationResult:
    """Pass iff the 12-digit CCCD parses cleanly."""
    try:
        parse_cccd(cccd)
    except CCCDFormatError as e:
        return _fail(str(e))
    return _ok()


def validate_ocr_consistency(ocr: OCRResult) -> ValidationResult:
    """Cross-check OCR'd fields against what the CCCD number itself encodes."""
    errors: list[str] = []
    warnings: list[str] = []

    if ocr.cccd is None:
        errors.append("OCR did not recognise CCCD field")
        return ValidationResult(is_valid=False, errors=tuple(errors))
    try:
        fields = parse_cccd(ocr.cccd)
    except CCCDFormatError as e:
        return _fail(f"CCCD parse failed: {e}")

    # Birth year vs CCCD-encoded birth year.
    if ocr.date_of_birth:
        dob = parse_date_dmy(ocr.date_of_birth)
        if dob is None:
            warnings.append(f"could not parse OCR date_of_birth {ocr.date_of_birth!r}")
        elif dob.year != fields.birth_year:
            errors.append(
                f"OCR date_of_birth year {dob.year} doesn't match CCCD-encoded "
                f"year {fields.birth_year}"
            )

    # Gender vs CCCD-encoded gender.
    if ocr.gender:
        g = parse_gender_text(ocr.gender)
        if g is None:
            warnings.append(f"could not parse OCR gender {ocr.gender!r}")
        elif g is not fields.gender:
            errors.append(
                f"OCR gender {g.value} doesn't match CCCD-encoded gender {fields.gender.value}"
            )

    if errors:
        return ValidationResult(is_valid=False, errors=tuple(errors), warnings=tuple(warnings))
    return ValidationResult(is_valid=True, warnings=tuple(warnings))


def validate_against_bca(ocr: OCRResult, bca: BCADatabase) -> ValidationResult:
    """Cross-check OCR'd fields against the BCA registry."""
    if ocr.cccd is None:
        return _fail("OCR has no CCCD to query BCA with")
    record = bca.lookup(ocr.cccd)
    if record is None:
        return _fail(f"CCCD {ocr.cccd} not found in BCA")
    return _cross_check_bca(ocr, record)


def _cross_check_bca(ocr: OCRResult, bca_record: BCARecord) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if ocr.full_name and ocr.full_name.strip().upper() != bca_record.full_name.upper():
        errors.append(f"name mismatch: OCR={ocr.full_name!r} vs BCA={bca_record.full_name!r}")
    if ocr.date_of_birth:
        dob = parse_date_dmy(ocr.date_of_birth)
        if dob is not None and dob != bca_record.date_of_birth:
            errors.append(
                f"DOB mismatch: OCR={dob.isoformat()} vs BCA={bca_record.date_of_birth.isoformat()}"
            )
    if ocr.gender:
        g = parse_gender_text(ocr.gender)
        if g is not None and g is not bca_record.gender:
            errors.append(f"gender mismatch: OCR={g.value} vs BCA={bca_record.gender.value}")
    if errors:
        return ValidationResult(is_valid=False, errors=tuple(errors), warnings=tuple(warnings))
    return ValidationResult(is_valid=True, warnings=tuple(warnings))


def merge(*results: ValidationResult) -> ValidationResult:
    """Combine multiple :class:`ValidationResult` into one (AND on validity)."""
    errors: list[str] = []
    warnings: list[str] = []
    is_valid = True
    for r in results:
        if not r.is_valid:
            is_valid = False
        errors.extend(r.errors)
        warnings.extend(r.warnings)
    return ValidationResult(is_valid=is_valid, errors=tuple(errors), warnings=tuple(warnings))


__all__ = [
    "ValidationResult",
    "merge",
    "parse_date_dmy",
    "parse_gender_text",
    "validate_against_bca",
    "validate_cccd_format",
    "validate_ocr_consistency",
]
