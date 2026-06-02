"""End-to-end eKYC pipeline.

Single entry point: :func:`process_image`. Takes an image (raw
bytes; PaddleOCR/VietOCR feed in the same byte buffer they got),
runs the OCR engine, validates the result against the CCCD encoding
+ BCA, and — if everything passes — produces an
:class:`EncryptedCitizenRecord`.

The pipeline is intentionally *fail-closed*: any validation error
suppresses encryption. The :class:`PipelineResult` always carries
the OCR output and the merged validation result so callers can
surface human-readable reasons in the UI / audit log.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ekycpipe.cccd import CCCDFormatError, parse_cccd
from ekycpipe.encryption import encrypt_record
from ekycpipe.schema import CitizenRecord

if TYPE_CHECKING:
    from datetime import date
from ekycpipe.validate import (
    ValidationResult,
    merge,
    parse_date_dmy,
    validate_against_bca,
    validate_cccd_format,
    validate_ocr_consistency,
)

if TYPE_CHECKING:
    from ekycpipe.bca import BCADatabase, BCARecord
    from ekycpipe.encryption import EncryptedCitizenRecord, KeyManager
    from ekycpipe.ocr import OCREngine
    from ekycpipe.schema import CCCDFields, OCRResult


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """The output the API would return per processed image."""

    ocr: OCRResult
    parsed_cccd: CCCDFields | None
    validation: ValidationResult
    bca_match: BCARecord | None
    encrypted: EncryptedCitizenRecord | None


def _to_citizen_record(
    ocr: OCRResult,
    bca_record: BCARecord,
) -> CitizenRecord | None:
    """Combine OCR + BCA into a structured citizen record.

    BCA is authoritative for name/DOB/gender/hometown; OCR provides
    place_of_residence + issued_at + expires_at (BCA doesn't return
    these). If either OCR field is missing, return ``None`` —
    caller can decide whether to soft-fail or surface a warning.
    """
    if ocr.cccd is None or ocr.issued_at is None or ocr.place_of_residence is None:
        return None
    issued = parse_date_dmy(ocr.issued_at)
    if issued is None:
        return None
    expires: date | None = None
    if ocr.expires_at:
        expires = parse_date_dmy(ocr.expires_at)
        if expires is None:
            return None
    return CitizenRecord(
        cccd=bca_record.cccd,
        full_name=bca_record.full_name,
        date_of_birth=bca_record.date_of_birth,
        gender=bca_record.gender,
        hometown_province_code=bca_record.hometown_province_code,
        place_of_residence=ocr.place_of_residence.strip(),
        issued_at=issued,
        expires_at=expires,
    )


def process_image(
    image: bytes,
    *,
    ocr: OCREngine,
    bca: BCADatabase,
    key_manager: KeyManager | None = None,
    policies: dict[str, str] | None = None,
) -> PipelineResult:
    """Run one image through the whole pipeline.

    If ``key_manager`` and ``policies`` are both supplied AND every
    validation step passes, the result's ``encrypted`` field is
    populated with an :class:`EncryptedCitizenRecord`. Otherwise
    ``encrypted`` is ``None`` — encryption is fail-closed on any
    validation issue.
    """
    ocr_result = ocr.recognize(image)

    # Step 1: OCR completeness.
    if not ocr_result.is_complete:
        return PipelineResult(
            ocr=ocr_result,
            parsed_cccd=None,
            validation=ValidationResult(
                is_valid=False, errors=("OCR did not recognise all required fields",)
            ),
            bca_match=None,
            encrypted=None,
        )

    # Step 2: parse the CCCD (we know it's non-None due to is_complete).
    assert ocr_result.cccd is not None
    cccd = ocr_result.cccd
    try:
        parsed = parse_cccd(cccd)
    except CCCDFormatError as e:
        return PipelineResult(
            ocr=ocr_result,
            parsed_cccd=None,
            validation=ValidationResult(is_valid=False, errors=(str(e),)),
            bca_match=None,
            encrypted=None,
        )

    # Step 3: run the three validation rules and merge.
    format_check = validate_cccd_format(cccd)
    consistency_check = validate_ocr_consistency(ocr_result)
    bca_check = validate_against_bca(ocr_result, bca)
    validation = merge(format_check, consistency_check, bca_check)

    bca_record = bca.lookup(cccd)

    # Step 4: encrypt iff fully valid + caller supplied a key manager.
    encrypted = None
    if (
        validation.is_valid
        and bca_record is not None
        and key_manager is not None
        and policies is not None
    ):
        record = _to_citizen_record(ocr_result, bca_record)
        if record is not None:
            encrypted = encrypt_record(record, key_manager, policies)

    return PipelineResult(
        ocr=ocr_result,
        parsed_cccd=parsed,
        validation=validation,
        bca_match=bca_record,
        encrypted=encrypted,
    )


__all__ = ["PipelineResult", "process_image"]
