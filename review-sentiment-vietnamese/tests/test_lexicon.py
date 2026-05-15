"""Lexicon + normalizer tests."""

from __future__ import annotations

from sentvn.lexicon import (
    INTENSIFIERS,
    NEGATIVE_WORDS,
    NEGATORS,
    POSITIVE_WORDS,
    normalize_vn_text,
    tokenize,
)


def test_normalize_strips_diacritics():
    assert normalize_vn_text("Tốt") == "tot"
    assert normalize_vn_text("TỐT") == "tot"
    assert normalize_vn_text("Đẹp") == "dep"


def test_normalize_preserves_ascii_lowercase():
    assert normalize_vn_text("hello") == "hello"


def test_normalize_handles_d_capital():
    assert normalize_vn_text("Đầu Tư") == "dau tu"


def test_tokenize_simple():
    assert tokenize("Sản phẩm rất tốt") == ["san", "pham", "rat", "tot"]


def test_tokenize_punctuation_split():
    assert tokenize("Tốt, nhanh") == ["tot", "nhanh"]


def test_tokenize_handles_underscore():
    """Multi-word phrases joined with underscore stay tokenised together."""
    assert "khong_the" in tokenize("Khong_the te hon")


def test_tokenize_empty_input():
    assert tokenize("") == []


def test_lexicon_is_ascii():
    """Every lexicon entry must be ASCII after normalization."""
    for word_set in (POSITIVE_WORDS, NEGATIVE_WORDS, INTENSIFIERS, NEGATORS):
        for word in word_set:
            assert word == word.lower()
            # Must not contain combining marks (would mean we forgot to normalize).
            assert all(ord(c) < 128 or c == "_" for c in word)


def test_lexicons_disjoint():
    """A word can only be one of positive/negative/intensifier/negator."""
    all_words = (POSITIVE_WORDS, NEGATIVE_WORDS, INTENSIFIERS, NEGATORS)
    for i, a in enumerate(all_words):
        for j, b in enumerate(all_words):
            if i < j:
                assert not (a & b), f"overlap: {a & b}"


def test_positive_lexicon_has_essentials():
    for word in ("tot", "dep", "nhanh", "yeu", "ung"):
        assert word in POSITIVE_WORDS


def test_negative_lexicon_has_essentials():
    for word in ("te", "kem", "cham", "gia", "lua"):
        assert word in NEGATIVE_WORDS
