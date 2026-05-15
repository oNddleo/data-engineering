"""Aggregation tests."""

from __future__ import annotations

import pytest

from sentvn.aggregations import by_category, by_product, by_seller, top_n, worst_n
from sentvn.classifier import LexiconClassifier
from sentvn.schema import SentimentLabel, SentimentResult

from ._fixtures import make_review


def _pairs():
    clf = LexiconClassifier()
    reviews = [
        make_review(
            review_id="R-1",
            seller_id=1,
            product_id=10,
            category_key="electronics",
            text="Rất tốt",
            rating_x100=500,
        ),
        make_review(
            review_id="R-2",
            seller_id=1,
            product_id=10,
            category_key="electronics",
            text="Tốt nhưng đắt",
            rating_x100=400,
        ),
        make_review(
            review_id="R-3",
            seller_id=2,
            product_id=11,
            category_key="fashion_women",
            text="Hàng giả, kém",
            rating_x100=100,
        ),
        make_review(
            review_id="R-4",
            seller_id=2,
            product_id=11,
            category_key="fashion_women",
            text="Bình thường",
            rating_x100=300,
        ),
    ]
    return [(rv, clf.classify(rv)) for rv in reviews]


def test_by_seller_buckets_correctly():
    buckets = by_seller(_pairs())
    assert "1" in buckets
    assert "2" in buckets
    assert buckets["1"].n_reviews == 2
    assert buckets["1"].n_positive == 1  # "Rất tốt"
    assert buckets["1"].n_neutral == 1  # "Tốt nhưng đắt"


def test_by_product_buckets():
    buckets = by_product(_pairs())
    assert buckets["10"].n_reviews == 2
    assert buckets["11"].n_reviews == 2


def test_by_category_buckets():
    buckets = by_category(_pairs())
    assert "electronics" in buckets
    assert "fashion_women" in buckets


def test_positive_negative_pct_arithmetic():
    buckets = by_seller(_pairs())
    b = buckets["2"]
    # 1 negative + 1 neutral.
    assert b.n_negative == 1
    assert b.negative_pct == 50.0
    assert b.positive_pct == 0.0


def test_net_promoter_pct():
    buckets = by_seller(_pairs())
    b = buckets["1"]
    # pos=50%, neg=0% → npp=+50.
    assert b.net_promoter_pct == 50.0


def test_top_n_sorts_descending_by_npp():
    buckets = by_seller(_pairs())
    ranked = top_n(buckets, n=10)
    # Seller 1 (npp=+50) > Seller 2 (npp=-50).
    assert ranked[0].key == "1"
    assert ranked[1].key == "2"


def test_worst_n_sorts_ascending_by_npp():
    buckets = by_seller(_pairs())
    ranked = worst_n(buckets, n=10)
    assert ranked[0].key == "2"


def test_top_n_respects_n():
    buckets = by_seller(_pairs())
    assert len(top_n(buckets, n=1)) == 1


def test_top_n_rejects_zero():
    with pytest.raises(ValueError):
        top_n({}, n=0)


def test_worst_n_rejects_zero():
    with pytest.raises(ValueError):
        worst_n({}, n=0)


def test_aggregate_rejects_mismatched_review_ids():
    rv = make_review(review_id="R-1")
    bad = SentimentResult(
        review_id="R-MISMATCH", label=SentimentLabel.POSITIVE, score=1, confidence=0.5
    )
    with pytest.raises(ValueError):
        by_seller([(rv, bad)])


def test_avg_score_in_bucket():
    buckets = by_seller(_pairs())
    b = buckets["1"]
    # "Rất tốt" = 2, "Tốt nhưng đắt" = 0. avg = 1.0
    assert b.avg_score == 1.0


def test_avg_rating_in_bucket():
    buckets = by_seller(_pairs())
    b = buckets["1"]
    # ratings 500 + 400 = 900 / 2 = 450.
    assert b.avg_rating_x100 == 450.0


def test_top_n_by_avg_score_alternative():
    buckets = by_seller(_pairs())
    ranked = top_n(buckets, n=10, by_npp=False)
    assert ranked[0].key == "1"  # higher avg_score
