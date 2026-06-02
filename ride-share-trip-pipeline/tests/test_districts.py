"""District directory lookups."""

from __future__ import annotations

from vntrip.districts import all_codes, by_city, is_valid, lookup


def test_lookup_known():
    d = lookup("HCM:Q1")
    assert d is not None
    assert d.name_vi == "Quận 1"
    assert d.city == "HCM"


def test_lookup_unknown_returns_none():
    assert lookup("XX:YYY") is None


def test_is_valid_true():
    assert is_valid("HN:HK") is True


def test_is_valid_false():
    assert is_valid("HN:XXX") is False
    assert is_valid("") is False


def test_by_city_hcm():
    """HCM has > 5 districts including Q1, Q3, BT, GV."""
    hcm = by_city("HCM")
    codes = {d.code for d in hcm}
    assert "HCM:Q1" in codes
    assert "HCM:BT" in codes
    assert "HCM:TD" in codes
    assert len(hcm) > 5


def test_by_city_hanoi():
    hn = by_city("HN")
    codes = {d.code for d in hn}
    assert "HN:HK" in codes
    assert "HN:BD" in codes
    assert len(hn) > 5


def test_by_city_danang():
    dn = by_city("DN")
    codes = {d.code for d in dn}
    assert "DN:HC" in codes
    assert len(dn) >= 3


def test_all_codes_alphabetical():
    codes = all_codes()
    assert codes == sorted(codes)
    assert len(codes) >= 15


def test_lookup_carries_vi_and_en_names():
    d = lookup("HN:HK")
    assert d is not None
    assert "Hoàn Kiếm" in d.name_vi
    assert d.name_en == "Hoan Kiem District"
