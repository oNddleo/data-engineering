"""ekyc-document-pipeline — CCCD parsing, BCA cross-check, column-level AEAD."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from ekycpipe.bca import BCADatabase, BCARecord
    from ekycpipe.cccd import CCCDFormatError, build_cccd, parse_cccd
    from ekycpipe.crypto import Cipher, HmacStreamCipher, IntegrityError, derive_key
    from ekycpipe.encryption import (
        SENSITIVE_COLUMNS,
        EncryptedCitizenRecord,
        KeyManager,
        cccd_index_hash,
        decrypt_record,
        encrypt_record,
    )
    from ekycpipe.ocr import MockOCREngine, OCREngine
    from ekycpipe.pipeline import PipelineResult, process_image
    from ekycpipe.provinces import PROVINCE_CODES, is_valid_province_code, province_name
    from ekycpipe.schema import CCCDFields, CitizenRecord, Gender, OCRResult
    from ekycpipe.simulator import generate
    from ekycpipe.validate import (
        ValidationResult,
        merge,
        parse_date_dmy,
        parse_gender_text,
        validate_against_bca,
        validate_cccd_format,
        validate_ocr_consistency,
    )


_LAZY: dict[str, tuple[str, str]] = {
    "BCADatabase": ("ekycpipe.bca", "BCADatabase"),
    "BCARecord": ("ekycpipe.bca", "BCARecord"),
    "CCCDFields": ("ekycpipe.schema", "CCCDFields"),
    "CCCDFormatError": ("ekycpipe.cccd", "CCCDFormatError"),
    "Cipher": ("ekycpipe.crypto", "Cipher"),
    "CitizenRecord": ("ekycpipe.schema", "CitizenRecord"),
    "EncryptedCitizenRecord": ("ekycpipe.encryption", "EncryptedCitizenRecord"),
    "Gender": ("ekycpipe.schema", "Gender"),
    "HmacStreamCipher": ("ekycpipe.crypto", "HmacStreamCipher"),
    "IntegrityError": ("ekycpipe.crypto", "IntegrityError"),
    "KeyManager": ("ekycpipe.encryption", "KeyManager"),
    "MockOCREngine": ("ekycpipe.ocr", "MockOCREngine"),
    "OCREngine": ("ekycpipe.ocr", "OCREngine"),
    "OCRResult": ("ekycpipe.schema", "OCRResult"),
    "PROVINCE_CODES": ("ekycpipe.provinces", "PROVINCE_CODES"),
    "PipelineResult": ("ekycpipe.pipeline", "PipelineResult"),
    "SENSITIVE_COLUMNS": ("ekycpipe.encryption", "SENSITIVE_COLUMNS"),
    "ValidationResult": ("ekycpipe.validate", "ValidationResult"),
    "build_cccd": ("ekycpipe.cccd", "build_cccd"),
    "cccd_index_hash": ("ekycpipe.encryption", "cccd_index_hash"),
    "decrypt_record": ("ekycpipe.encryption", "decrypt_record"),
    "derive_key": ("ekycpipe.crypto", "derive_key"),
    "encrypt_record": ("ekycpipe.encryption", "encrypt_record"),
    "generate": ("ekycpipe.simulator", "generate"),
    "is_valid_province_code": ("ekycpipe.provinces", "is_valid_province_code"),
    "merge": ("ekycpipe.validate", "merge"),
    "parse_cccd": ("ekycpipe.cccd", "parse_cccd"),
    "parse_date_dmy": ("ekycpipe.validate", "parse_date_dmy"),
    "parse_gender_text": ("ekycpipe.validate", "parse_gender_text"),
    "process_image": ("ekycpipe.pipeline", "process_image"),
    "province_name": ("ekycpipe.provinces", "province_name"),
    "validate_against_bca": ("ekycpipe.validate", "validate_against_bca"),
    "validate_cccd_format": ("ekycpipe.validate", "validate_cccd_format"),
    "validate_ocr_consistency": ("ekycpipe.validate", "validate_ocr_consistency"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PROVINCE_CODES",
    "SENSITIVE_COLUMNS",
    "BCADatabase",
    "BCARecord",
    "CCCDFields",
    "CCCDFormatError",
    "Cipher",
    "CitizenRecord",
    "EncryptedCitizenRecord",
    "Gender",
    "HmacStreamCipher",
    "IntegrityError",
    "KeyManager",
    "MockOCREngine",
    "OCREngine",
    "OCRResult",
    "PipelineResult",
    "ValidationResult",
    "__version__",
    "build_cccd",
    "cccd_index_hash",
    "decrypt_record",
    "derive_key",
    "encrypt_record",
    "generate",
    "is_valid_province_code",
    "merge",
    "parse_cccd",
    "parse_date_dmy",
    "parse_gender_text",
    "process_image",
    "province_name",
    "validate_against_bca",
    "validate_cccd_format",
    "validate_ocr_consistency",
]
