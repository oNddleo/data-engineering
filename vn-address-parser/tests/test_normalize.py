"""Diacritic-folding + abbreviation expansion."""

from __future__ import annotations

from vnaddr.normalize import (
    expand_abbreviations,
    fold_diacritics,
    normalise,
    tokens,
)

# ---------- fold_diacritics --------------------------------------------------


def test_fold_basic():
    assert fold_diacritics("Hồ Chí Minh") == "ho chi minh"


def test_fold_all_vowels():
    assert fold_diacritics("àáảãạăắằẳẵặâấầẩẫậ") == "a" * 17


def test_fold_d_stroked():
    assert fold_diacritics("Đà Nẵng") == "da nang"


def test_fold_passes_ascii_unchanged():
    assert fold_diacritics("hello world") == "hello world"


def test_fold_keeps_digits_and_punct():
    assert fold_diacritics("Quận 1, Hồ Chí Minh") == "quan 1, ho chi minh"


# ---------- expand_abbreviations ---------------------------------------------


def test_expand_tphcm():
    assert expand_abbreviations("TP.HCM") == "thành phố hồ chí minh"
    assert expand_abbreviations("tphcm") == "thành phố hồ chí minh"
    assert expand_abbreviations("TP HCM") == "thành phố hồ chí minh"


def test_expand_quan_n():
    assert expand_abbreviations("Q.1") == "quận 1"
    assert expand_abbreviations("Q1") == "quận 1"
    assert expand_abbreviations("Quan 1") == "quận 1"


def test_expand_phuong_n():
    assert expand_abbreviations("P.5") == "phường 5"
    assert expand_abbreviations("P5") == "phường 5"


def test_expand_phuong_named():
    assert "phường " in expand_abbreviations("P. Bến Nghé")


def test_expand_tp_hn():
    assert expand_abbreviations("TP.HN") == "thành phố hà nội"


def test_expand_no_match_passes_through():
    assert expand_abbreviations("hello world") == "hello world"


# ---------- normalise pipeline -----------------------------------------------


def test_normalise_pipeline():
    """End-to-end: lowercase + expand + fold + collapse whitespace."""
    out = normalise("  Q.1, TP. HCM  ")
    assert out == "quan 1, thanh pho ho chi minh"


def test_normalise_full_address():
    out = normalise("Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh")
    assert out == "phuong ben nghe, quan 1, thanh pho ho chi minh"


def test_normalise_empty():
    assert normalise("") == ""


# ---------- tokens -----------------------------------------------------------


def test_tokens_comma_split():
    out = tokens("a, b, c")
    assert out == ["a", "b", "c"]


def test_tokens_slash_split():
    out = tokens("a/b/c")
    assert out == ["a", "b", "c"]


def test_tokens_mixed_separator():
    out = tokens("a, b/c, d")
    assert out == ["a", "b", "c", "d"]


def test_tokens_drops_empty():
    assert tokens(",, , a, ,") == ["a"]
