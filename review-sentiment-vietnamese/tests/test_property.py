"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from sentvn.classifier import score_text, score_to_label
from sentvn.io_jsonl import review_from_dict, review_to_dict
from sentvn.lexicon import normalize_vn_text

from ._fixtures import make_review


@given(rating=st.integers(min_value=0, max_value=500))
def test_review_round_trips(rating):
    r = make_review(rating_x100=rating)
    assert review_from_dict(review_to_dict(r)) == r


@given(text=st.text(min_size=0, max_size=100))
def test_normalize_idempotent(text):
    """Property: normalize(normalize(x)) == normalize(x)."""
    once = normalize_vn_text(text)
    twice = normalize_vn_text(once)
    assert once == twice


@given(text=st.text(min_size=0, max_size=200))
def test_score_text_total_function(text):
    """Property: score_text never raises for any text."""
    score, hits = score_text(text)
    assert isinstance(score, int)
    assert hits >= 0


@given(text=st.text(min_size=0, max_size=200))
def test_score_to_label_total(text):
    """Property: score_to_label is total for any computed score."""
    score, _ = score_text(text)
    label = score_to_label(score)
    assert label.value in ("POSITIVE", "NEGATIVE", "NEUTRAL")


@given(
    n_positive_words=st.integers(min_value=0, max_value=5),
    n_negative_words=st.integers(min_value=0, max_value=5),
)
def test_score_sign_matches_word_majority(n_positive_words, n_negative_words):
    """Property: with no intensifiers/negators, score sign matches the majority count."""
    text = " ".join(["tot"] * n_positive_words + ["te"] * n_negative_words)
    score, _ = score_text(text)
    expected = n_positive_words - n_negative_words
    assert score == expected
