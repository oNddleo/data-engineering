"""Card prefix decoding + ICD-10-VN lookup."""

from __future__ import annotations

import pytest

from bhyt.card import decode_prefix, is_valid_format, normalise
from bhyt.icd10vn import bundled_codes, codes_by_chapter, lookup
from bhyt.schema import ExemptionCategory

# ---------- card -----------------------------------------------------------


def test_decode_employer_uu_tien_4():
    info = decode_prefix("D40179012345678")
    assert info.scheme_letter == "D"
    assert info.priority_letter == "4"
    assert info.category is ExemptionCategory.UU_TIEN_4
    assert "Doanh nghiệp" in info.scheme_name


def test_decode_child_uu_tien_1():
    info = decode_prefix("T10179012345678")
    assert info.category is ExemptionCategory.UU_TIEN_1


def test_decode_war_veteran_uu_tien_2():
    info = decode_prefix("X20179012345678")
    assert info.category is ExemptionCategory.UU_TIEN_2


def test_decode_voluntary_uu_tien_5():
    info = decode_prefix("G50179012345678")
    assert info.category is ExemptionCategory.UU_TIEN_5


def test_decode_rejects_bad_format():
    with pytest.raises(ValueError):
        decode_prefix("BAD")


def test_decode_rejects_unknown_scheme():
    """Z is not a registered scheme letter."""
    with pytest.raises(ValueError):
        decode_prefix("Z10179012345678")


def test_decode_rejects_invalid_priority():
    """0 is not a valid priority digit."""
    with pytest.raises(ValueError):
        decode_prefix("D00179012345678")


def test_is_valid_format_true_cases():
    for c in ("D40179012345678", "T10179012345678", "G50179012345678"):
        assert is_valid_format(c)


def test_is_valid_format_false_cases():
    bad_cases = [
        "",
        "TOOSHORT",
        "D4017901234567A",  # non-digit suffix
        "DA0179012345678",  # priority is a letter not digit
        "440179012345678",  # scheme is digit not letter
        "Z40179012345678",  # unknown scheme letter
        "D60179012345678",  # priority out of range
    ]
    for bad in bad_cases:
        assert not is_valid_format(bad), f"expected {bad!r} to fail"


def test_normalise_strips_whitespace_and_upcases():
    assert normalise("  d4 0179012345678 ") == "D40179012345678"


# ---------- ICD-10-VN -----------------------------------------------------


def test_lookup_known_code_returns_entry():
    entry = lookup("I10")
    assert entry is not None
    assert "Tăng huyết áp" in entry.name_vi


def test_lookup_case_insensitive():
    entry = lookup("i10")
    assert entry is not None
    assert entry.code == "I10"


def test_lookup_subcode_falls_back_to_parent():
    """E11.9 (T2DM with no complications) maps to E11 for billing."""
    entry = lookup("E11.9")
    assert entry is not None
    assert entry.code == "E11"


def test_lookup_unknown_returns_none():
    assert lookup("Z99") is None


def test_lookup_empty_returns_none():
    assert lookup("") is None


def test_bundled_codes_non_empty():
    assert len(bundled_codes()) > 0


def test_codes_by_chapter_filters():
    """Chapter I contains circulatory diseases — hypertension etc."""
    i_chapter = codes_by_chapter("I")
    codes = {e.code for e in i_chapter}
    assert "I10" in codes


def test_codes_by_chapter_empty_for_unknown():
    """No bundled codes in chapter Y."""
    assert codes_by_chapter("Y") == ()
