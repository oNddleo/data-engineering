"""CCCD parser tests."""

from __future__ import annotations

import pytest

from ekycpipe.cccd import CCCDFormatError, build_cccd, parse_cccd
from ekycpipe.schema import Gender


def test_parse_hcm_male_1995():
    """079 = HCM, 0=male+19xx, 95 = 1995, 012345 = serial."""
    f = parse_cccd("079095012345")
    assert f.province_code == "079"
    assert f.gender is Gender.MALE
    assert f.century == 19
    assert f.birth_year_yy == 95
    assert f.birth_year == 1995
    assert f.serial == "012345"


def test_parse_hn_female_2002():
    """001 = HN, 3=female+20xx, 02 = 2002, 654321 = serial."""
    f = parse_cccd("001302654321")
    assert f.province_code == "001"
    assert f.gender is Gender.FEMALE
    assert f.century == 20
    assert f.birth_year_yy == 2
    assert f.birth_year == 2002


def test_parse_rejects_wrong_length():
    with pytest.raises(CCCDFormatError):
        parse_cccd("12345")
    with pytest.raises(CCCDFormatError):
        parse_cccd("0790950123456")


def test_parse_rejects_non_digit():
    with pytest.raises(CCCDFormatError):
        parse_cccd("07909501234A")


def test_parse_rejects_unknown_province():
    # Province 003 is a gap in the official table.
    with pytest.raises(CCCDFormatError):
        parse_cccd("003095012345")


def test_parse_century_decoding_table():
    # 0/1 → 19xx, 2/3 → 20xx, 4/5 → 21xx, 6/7 → 22xx, 8/9 → 23xx
    centuries_for_gc = {
        "0": (Gender.MALE, 19),
        "1": (Gender.FEMALE, 19),
        "2": (Gender.MALE, 20),
        "3": (Gender.FEMALE, 20),
        "4": (Gender.MALE, 21),
        "5": (Gender.FEMALE, 21),
        "6": (Gender.MALE, 22),
        "7": (Gender.FEMALE, 22),
        "8": (Gender.MALE, 23),
        "9": (Gender.FEMALE, 23),
    }
    for digit, (gender, century) in centuries_for_gc.items():
        cccd = f"079{digit}95012345"
        f = parse_cccd(cccd)
        assert f.gender is gender, digit
        assert f.century == century, digit


def test_parse_strips_whitespace():
    assert parse_cccd("  079095012345  ").province_code == "079"


def test_build_round_trips_parse():
    cccd = build_cccd(province_code="079", gender=Gender.MALE, birth_year=1995, serial="012345")
    f = parse_cccd(cccd)
    assert f.province_code == "079"
    assert f.gender is Gender.MALE
    assert f.birth_year == 1995
    assert f.serial == "012345"


def test_build_rejects_bad_province():
    with pytest.raises(CCCDFormatError):
        build_cccd(province_code="003", gender=Gender.MALE, birth_year=1995, serial="012345")


def test_build_rejects_out_of_range_year():
    with pytest.raises(CCCDFormatError):
        build_cccd(province_code="079", gender=Gender.MALE, birth_year=1800, serial="012345")
    with pytest.raises(CCCDFormatError):
        build_cccd(province_code="079", gender=Gender.MALE, birth_year=2500, serial="012345")


def test_build_rejects_bad_serial():
    with pytest.raises(CCCDFormatError):
        build_cccd(province_code="079", gender=Gender.MALE, birth_year=1995, serial="ABC")
    with pytest.raises(CCCDFormatError):
        build_cccd(
            province_code="079", gender=Gender.MALE, birth_year=1995, serial="12345"
        )  # 5 digits


def test_build_handles_2100s():
    """4 = male/21xx — a Cô Bé Trà My born in 2105 would get a CCCD digit 4."""
    cccd = build_cccd(province_code="079", gender=Gender.MALE, birth_year=2105, serial="000001")
    f = parse_cccd(cccd)
    assert f.century == 21
    assert f.birth_year == 2105
