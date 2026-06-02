"""Schema invariants."""

from __future__ import annotations

from datetime import date

import pytest

from ekycpipe.schema import CCCDFields, Gender

from ._fixtures import hcm_male_1995_serial, make_citizen, make_ocr


def test_gender_enum_values():
    assert {g.value for g in Gender} == {"MALE", "FEMALE"}


def test_cccd_fields_birth_year_property():
    f = CCCDFields(
        province_code="079", gender=Gender.MALE, century=20, birth_year_yy=2, serial="000001"
    )
    assert f.birth_year == 2002


def test_ocr_result_is_complete_happy_path():
    o = make_ocr()
    assert o.is_complete


def test_ocr_result_incomplete_when_cccd_missing():
    o = make_ocr(cccd=None)
    assert not o.is_complete


def test_ocr_result_incomplete_when_blank_name():
    o = make_ocr(full_name="")
    assert not o.is_complete


def test_citizen_record_happy_path():
    r = make_citizen()
    assert r.cccd == hcm_male_1995_serial()


def test_citizen_record_rejects_empty_cccd():
    with pytest.raises(ValueError):
        make_citizen(cccd="")


def test_citizen_record_rejects_blank_name():
    with pytest.raises(ValueError):
        make_citizen(full_name="   ")


def test_citizen_record_rejects_empty_province():
    with pytest.raises(ValueError):
        make_citizen(hometown_province_code="")


def test_citizen_record_rejects_expiry_before_issue():
    with pytest.raises(ValueError):
        make_citizen(issued_at=date(2024, 1, 1), expires_at=date(2023, 1, 1))


def test_citizen_record_accepts_none_expiry():
    r = make_citizen(expires_at=None)
    assert r.expires_at is None
