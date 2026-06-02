"""Province-code registry tests."""

from __future__ import annotations

from ekycpipe.provinces import PROVINCE_CODES, is_valid_province_code, province_name


def test_known_codes_resolve():
    assert province_name("001") == "Hà Nội"
    assert province_name("079") == "TP. Hồ Chí Minh"
    assert province_name("031") == "Hải Phòng"
    assert province_name("048") == "Đà Nẵng"
    assert province_name("092") == "Cần Thơ"


def test_unknown_code_returns_none():
    assert province_name("003") is None
    assert province_name("999") is None
    assert province_name("ABC") is None


def test_is_valid_province_code():
    assert is_valid_province_code("001")
    assert is_valid_province_code("079")
    assert not is_valid_province_code("003")  # gap in the table
    assert not is_valid_province_code("ABC")
    assert not is_valid_province_code("99")  # wrong length
    assert not is_valid_province_code("0001")  # wrong length


def test_registry_has_63_provinces():
    assert len(PROVINCE_CODES) == 63


def test_all_codes_are_3_digit_numeric():
    for code in PROVINCE_CODES:
        assert len(code) == 3
        assert code.isdigit()


def test_codes_within_expected_range():
    for code in PROVINCE_CODES:
        n = int(code)
        assert 1 <= n <= 96
