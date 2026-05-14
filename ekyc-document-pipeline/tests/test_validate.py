"""Validation rule tests."""

from __future__ import annotations

from datetime import date

from ekycpipe.bca import BCADatabase
from ekycpipe.schema import Gender
from ekycpipe.validate import (
    merge,
    parse_date_dmy,
    parse_gender_text,
    validate_against_bca,
    validate_cccd_format,
    validate_ocr_consistency,
)

from ._fixtures import hcm_male_1995_serial, make_bca, make_ocr


def test_parse_gender_text_vn():
    assert parse_gender_text("Nam") is Gender.MALE
    assert parse_gender_text("Nữ") is Gender.FEMALE
    assert parse_gender_text("Male") is Gender.MALE
    assert parse_gender_text("FEMALE") is Gender.FEMALE
    assert parse_gender_text("xxx") is None


def test_parse_date_dmy_accepts_three_formats():
    assert parse_date_dmy("15/05/1995") == date(1995, 5, 15)
    assert parse_date_dmy("15-05-1995") == date(1995, 5, 15)
    assert parse_date_dmy("1995-05-15") == date(1995, 5, 15)


def test_parse_date_dmy_returns_none_on_garbage():
    assert parse_date_dmy("not-a-date") is None
    assert parse_date_dmy("32/13/9999") is None


def test_validate_cccd_format_pass():
    r = validate_cccd_format(hcm_male_1995_serial())
    assert r.is_valid


def test_validate_cccd_format_fails_on_garbage():
    r = validate_cccd_format("000000000000")
    assert not r.is_valid
    assert any("province" in e.lower() for e in r.errors)


def test_validate_consistency_happy_path():
    r = validate_ocr_consistency(make_ocr())
    assert r.is_valid


def test_validate_consistency_dob_year_mismatch():
    """OCR says 1980 but CCCD encodes 1995 → error."""
    ocr = make_ocr(date_of_birth="15/05/1980")
    r = validate_ocr_consistency(ocr)
    assert not r.is_valid


def test_validate_consistency_gender_mismatch():
    """OCR says Nữ but CCCD encodes male → error."""
    ocr = make_ocr(gender="Nữ")
    r = validate_ocr_consistency(ocr)
    assert not r.is_valid


def test_validate_consistency_missing_cccd_fails():
    ocr = make_ocr(cccd=None)
    r = validate_ocr_consistency(ocr)
    assert not r.is_valid


def test_validate_consistency_unparseable_dob_warns_only():
    ocr = make_ocr(date_of_birth="???")
    r = validate_ocr_consistency(ocr)
    assert r.is_valid  # still passes
    assert r.warnings


def test_validate_against_bca_hit():
    bca = BCADatabase([make_bca()])
    r = validate_against_bca(make_ocr(), bca)
    assert r.is_valid


def test_validate_against_bca_miss():
    bca = BCADatabase([])
    r = validate_against_bca(make_ocr(), bca)
    assert not r.is_valid
    assert any("BCA" in e for e in r.errors)


def test_validate_against_bca_name_mismatch():
    bca = BCADatabase([make_bca()])
    ocr = make_ocr(full_name="Trần Văn B")
    r = validate_against_bca(ocr, bca)
    assert not r.is_valid


def test_validate_against_bca_case_insensitive_name():
    bca = BCADatabase([make_bca()])
    ocr = make_ocr(full_name="NGUYỄN VĂN A")
    r = validate_against_bca(ocr, bca)
    assert r.is_valid  # uppercase matches


def test_validate_against_bca_dob_mismatch():
    bca = BCADatabase([make_bca()])
    ocr = make_ocr(date_of_birth="01/01/1980")
    r = validate_against_bca(ocr, bca)
    assert not r.is_valid


def test_validate_against_bca_no_cccd_fails():
    bca = BCADatabase([make_bca()])
    ocr = make_ocr(cccd=None)
    r = validate_against_bca(ocr, bca)
    assert not r.is_valid


def test_merge_all_valid():
    from ekycpipe.validate import ValidationResult

    a = ValidationResult(is_valid=True)
    b = ValidationResult(is_valid=True, warnings=("w1",))
    out = merge(a, b)
    assert out.is_valid
    assert out.warnings == ("w1",)


def test_merge_one_invalid_makes_all_invalid():
    from ekycpipe.validate import ValidationResult

    a = ValidationResult(is_valid=True)
    b = ValidationResult(is_valid=False, errors=("e1",))
    out = merge(a, b)
    assert not out.is_valid
    assert "e1" in out.errors


def test_merge_concatenates_errors_and_warnings():
    from ekycpipe.validate import ValidationResult

    a = ValidationResult(is_valid=False, errors=("e1",), warnings=("w1",))
    b = ValidationResult(is_valid=False, errors=("e2",), warnings=("w2",))
    out = merge(a, b)
    assert set(out.errors) == {"e1", "e2"}
    assert set(out.warnings) == {"w1", "w2"}
