"""LexiconClassifier tests."""

from __future__ import annotations

from sentvn.classifier import LexiconClassifier, score_text, score_to_label
from sentvn.schema import SentimentLabel

from ._fixtures import make_review


def test_score_simple_positive():
    score, hits = score_text("Tốt")
    assert score == 1
    assert hits == 1


def test_score_simple_negative():
    score, hits = score_text("Tệ")
    assert score == -1
    assert hits == 1


def test_score_neutral_text():
    score, hits = score_text("Sản phẩm thông thường")
    assert score == 0
    assert hits == 0


def test_score_intensified_positive():
    score, _ = score_text("Rất tốt")
    assert score == 2  # 1 × 2


def test_score_double_intensified():
    score, _ = score_text("Rất cực tốt")
    assert score == 4  # 1 × 2 × 2


def test_score_negated_positive():
    score, _ = score_text("Không tốt")
    assert score == -1


def test_score_intensified_negation():
    score, _ = score_text("Rất không tốt")
    assert score == -2  # negated then intensified


def test_score_negated_then_intensified_positive():
    """Order: negator first, then intensifier. Both apply to the next sentiment word."""
    score, _ = score_text("Không rất tốt")
    # negate=True, intensify=2 → tot=+1, negated → -1, *2 = -2
    assert score == -2


def test_score_mixed_positive_negative():
    score, _ = score_text("Tốt nhưng chậm")
    assert score == 0  # +1 + (-1) = 0


def test_score_classifies_review_via_classify():
    clf = LexiconClassifier()
    r = clf.classify(make_review(text="Rất tốt"))
    assert r.label is SentimentLabel.POSITIVE
    assert r.score == 2


def test_classify_text_returns_empty_review_id():
    clf = LexiconClassifier()
    r = clf.classify_text("Tốt")
    assert r.review_id == ""


def test_score_to_label_mapping():
    assert score_to_label(5) is SentimentLabel.POSITIVE
    assert score_to_label(-3) is SentimentLabel.NEGATIVE
    assert score_to_label(0) is SentimentLabel.NEUTRAL


def test_confidence_zero_for_no_hits():
    clf = LexiconClassifier()
    r = clf.classify_text("Mua đi đi")
    assert r.confidence == 0.0


def test_confidence_clamped_to_1():
    clf = LexiconClassifier()
    # Strongly positive — confidence should be high but capped at 1.
    r = clf.classify_text("Rất rất tốt")
    assert 0 <= r.confidence <= 1.0


def test_confidence_increases_with_score():
    clf = LexiconClassifier()
    weak = clf.classify_text("Tốt nhưng đắt")  # 0
    strong = clf.classify_text("Rất tốt")  # 2
    assert strong.confidence > weak.confidence


def test_classify_diacritics_robust():
    clf = LexiconClassifier()
    # Same review in three forms — all should classify identically.
    for text in ("Rất tốt", "rat tot", "RẤT TỐT"):
        r = clf.classify_text(text)
        assert r.label is SentimentLabel.POSITIVE
        assert r.score == 2


def test_classify_complex_review():
    """Realistic Shopee-style positive review."""
    clf = LexiconClassifier()
    r = clf.classify_text("Sản phẩm rất đẹp, giao hàng nhanh, shop yêu lắm")
    assert r.label is SentimentLabel.POSITIVE
    assert r.score >= 3


def test_classify_complex_negative_review():
    clf = LexiconClassifier()
    r = clf.classify_text("Hàng giả, không nên mua, kém chất lượng")
    assert r.label is SentimentLabel.NEGATIVE


def test_score_lone_intensifier_no_effect():
    """An intensifier without a following sentiment word doesn't contribute."""
    score, hits = score_text("Rất ok")
    assert hits == 0  # "ok" not in lexicon


def test_score_lone_negator_no_effect():
    score, hits = score_text("Không bình thường")
    assert hits == 0  # "binh thuong" not in lexicon
