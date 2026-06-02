"""End-to-end pipeline tests."""

from __future__ import annotations

from ekycpipe.bca import BCADatabase
from ekycpipe.encryption import SENSITIVE_COLUMNS, KeyManager
from ekycpipe.ocr import MockOCREngine
from ekycpipe.pipeline import process_image

from ._fixtures import hcm_male_1995_serial, make_bca, make_ocr


def _km() -> KeyManager:
    return KeyManager({"K-PII": b"\x07" * 32})


def _policies() -> dict[str, str]:
    return {c: "K-PII" for c in SENSITIVE_COLUMNS}


def test_pipeline_happy_path_with_encryption():
    img = b"IMG-1"
    ocr_engine = MockOCREngine({img: make_ocr()})
    bca = BCADatabase([make_bca()])
    result = process_image(img, ocr=ocr_engine, bca=bca, key_manager=_km(), policies=_policies())
    assert result.validation.is_valid
    assert result.encrypted is not None
    assert result.parsed_cccd is not None
    assert result.parsed_cccd.birth_year == 1995
    assert result.bca_match is not None


def test_pipeline_happy_path_without_encryption_skips_encrypted():
    img = b"IMG-1"
    ocr_engine = MockOCREngine({img: make_ocr()})
    bca = BCADatabase([make_bca()])
    result = process_image(img, ocr=ocr_engine, bca=bca)
    assert result.validation.is_valid
    assert result.encrypted is None  # no KM passed


def test_pipeline_fails_when_ocr_returns_nothing():
    img = b"UNKNOWN"
    ocr_engine = MockOCREngine({})  # no canned response
    bca = BCADatabase([make_bca()])
    result = process_image(img, ocr=ocr_engine, bca=bca)
    assert not result.validation.is_valid
    assert result.encrypted is None


def test_pipeline_fails_when_cccd_not_in_bca():
    img = b"IMG-1"
    ocr_engine = MockOCREngine({img: make_ocr()})
    bca = BCADatabase([])  # empty registry
    result = process_image(img, ocr=ocr_engine, bca=bca, key_manager=_km(), policies=_policies())
    assert not result.validation.is_valid
    assert result.encrypted is None  # fail-closed


def test_pipeline_fails_when_ocr_dob_inconsistent_with_cccd():
    img = b"IMG-1"
    bad_ocr = make_ocr(date_of_birth="15/05/1980")  # CCCD encodes 1995
    ocr_engine = MockOCREngine({img: bad_ocr})
    bca = BCADatabase([make_bca()])
    result = process_image(img, ocr=ocr_engine, bca=bca, key_manager=_km(), policies=_policies())
    assert not result.validation.is_valid
    assert result.encrypted is None


def test_pipeline_fails_when_ocr_name_mismatches_bca():
    img = b"IMG-1"
    ocr_engine = MockOCREngine({img: make_ocr(full_name="Wrong Person")})
    bca = BCADatabase([make_bca(full_name="Nguyễn Văn A")])
    result = process_image(img, ocr=ocr_engine, bca=bca, key_manager=_km(), policies=_policies())
    assert not result.validation.is_valid
    assert result.encrypted is None


def test_pipeline_carries_ocr_through_failure():
    """Even on failure, pipeline should return the OCR result so the UI can show it."""
    img = b"IMG-1"
    bad_ocr = make_ocr(cccd="000000000000")
    ocr_engine = MockOCREngine({img: bad_ocr})
    bca = BCADatabase([])
    result = process_image(img, ocr=ocr_engine, bca=bca)
    assert result.ocr == bad_ocr
    assert not result.validation.is_valid


def test_pipeline_round_trip_encrypted_record():
    """Decrypt the pipeline's encrypted output and check the citizen we get out."""
    from ekycpipe.encryption import decrypt_record

    img = b"IMG-1"
    ocr_engine = MockOCREngine({img: make_ocr()})
    bca = BCADatabase([make_bca()])
    km = _km()
    policies = _policies()
    result = process_image(img, ocr=ocr_engine, bca=bca, key_manager=km, policies=policies)
    assert result.encrypted is not None
    decrypted = decrypt_record(result.encrypted, km, policies)
    assert decrypted.cccd == hcm_male_1995_serial()
    assert decrypted.full_name == "Nguyễn Văn A"
