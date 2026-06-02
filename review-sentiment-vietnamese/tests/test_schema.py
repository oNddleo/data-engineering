"""Schema invariants."""

from __future__ import annotations

from datetime import datetime

import pytest

from sentvn.schema import VN_TZ, SentimentLabel, SentimentResult

from ._fixtures import make_review


def test_label_enum():
    assert {label.value for label in SentimentLabel} == {"POSITIVE", "NEGATIVE", "NEUTRAL"}


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_review_happy_path():
    r = make_review()
    assert r.rating_x100 == 450


def test_review_rejects_empty_id():
    with pytest.raises(ValueError):
        make_review(review_id="")


def test_review_rejects_non_positive_seller():
    with pytest.raises(ValueError):
        make_review(seller_id=0)


def test_review_rejects_non_positive_product():
    with pytest.raises(ValueError):
        make_review(product_id=-1)


def test_review_rejects_empty_category():
    with pytest.raises(ValueError):
        make_review(category_key="")


def test_review_rejects_invalid_rating():
    with pytest.raises(ValueError):
        make_review(rating_x100=600)
    with pytest.raises(ValueError):
        make_review(rating_x100=-1)


def test_review_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_review(posted_at=datetime(2026, 5, 14))


def test_sentiment_result_rejects_bad_confidence():
    with pytest.raises(ValueError):
        SentimentResult(review_id="R", label=SentimentLabel.POSITIVE, score=1, confidence=1.5)
    with pytest.raises(ValueError):
        SentimentResult(review_id="R", label=SentimentLabel.POSITIVE, score=1, confidence=-0.1)
