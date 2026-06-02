"""End-to-end parser tests."""

from __future__ import annotations

from vnaddr.parser import parse
from vnaddr.schema import MatchKind


def test_parse_clean_full_address():
    """Canonical address parses cleanly into all three levels."""
    p = parse("123 Lê Lợi, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh")
    assert p.is_complete
    assert p.street == "123 Lê Lợi"
    assert p.ward is not None and p.ward.matched_name == "Phường Bến Nghé"
    assert p.district is not None and p.district.matched_name == "Quận 1"
    assert p.province is not None and p.province.matched_name == "Thành phố Hồ Chí Minh"


def test_parse_with_abbreviations():
    """Q.1, P. Bến Nghé, TP.HCM all expand correctly."""
    p = parse("50 Đồng Khởi, P. Bến Nghé, Q.1, TP.HCM")
    assert p.is_complete
    assert p.province is not None
    assert p.province.matched_code == "HCM"


def test_parse_diacritic_folded_input():
    """No-diacritics input still resolves."""
    p = parse("50 Le Loi, Phuong Ben Nghe, Quan 1, Thanh pho Ho Chi Minh")
    assert p.is_complete
    assert p.district is not None
    assert p.district.matched_code == "HCM:Q1"


def test_parse_fuzzy_match_typo():
    """A 1-char typo in province name still resolves via fuzzy."""
    p = parse("Hoàn Kiếm, Hà Nọi")  # "Nọi" instead of "Nội"
    assert p.province is not None
    assert p.province.matched_code == "HN"
    assert p.province.kind in (MatchKind.FUZZY, MatchKind.EXACT)


def test_parse_missing_ward():
    """An address with only district + province is partial, not complete."""
    p = parse("Quận Hoàn Kiếm, Thành phố Hà Nội")
    assert p.is_complete is False
    assert p.is_partial is True
    assert p.district is not None
    assert p.province is not None


def test_parse_only_province():
    p = parse("Đà Nẵng")
    assert p.province is not None
    assert p.province.matched_code == "DN"


def test_parse_pure_garbage_returns_failed():
    """Random text → no admin matches."""
    p = parse("zzz xxx yyy random")
    assert p.is_partial is False
    assert p.is_complete is False


def test_parse_empty_string():
    p = parse("")
    assert p.is_partial is False
    assert p.street == ""


def test_parse_strips_address_prefix():
    """'Hồ Chí Minh' (without 'Thành phố') still resolves via prefix strip."""
    p = parse("Hồ Chí Minh")
    assert p.province is not None
    assert p.province.matched_code == "HCM"


def test_parse_normalised_output_consistent():
    """The normalised output preserves all three levels."""
    p = parse("123 Đồng Khởi, Phường Bến Nghé, Quận 1, Hồ Chí Minh")
    assert p.is_complete
    # The normalised form should contain canonical names for each level.
    assert "Phường Bến Nghé" in p.normalised
    assert "Quận 1" in p.normalised


def test_parse_handles_extra_whitespace():
    p = parse("  123   Lê Lợi  ,  Phường Bến Nghé , Quận 1 ,  TP.HCM  ")
    assert p.is_complete


def test_parse_da_nang_address():
    """Đà Nẵng address with Hải Châu district."""
    p = parse("12 Bạch Đằng, Quận Hải Châu, Đà Nẵng")
    assert p.province is not None
    assert p.province.matched_code == "DN"
    assert p.district is not None
    assert p.district.matched_code == "DN:HC"


def test_parse_includes_raw_input():
    """The original raw input is preserved on the result."""
    raw = "50 Đồng Khởi, Phường Bến Nghé, Quận 1, TP.HCM"
    p = parse(raw)
    assert p.raw_input == raw
