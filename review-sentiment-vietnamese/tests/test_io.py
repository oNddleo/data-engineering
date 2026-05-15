"""JSONL codec tests."""

from __future__ import annotations

from sentvn.io_jsonl import (
    dump_results,
    dump_reviews,
    load_results,
    load_reviews,
    result_from_dict,
    result_to_dict,
    review_from_dict,
    review_to_dict,
)
from sentvn.schema import SentimentLabel, SentimentResult

from ._fixtures import make_review


def test_review_round_trip():
    r = make_review()
    assert review_from_dict(review_to_dict(r)) == r


def test_review_jsonl_round_trip():
    rs = [make_review(review_id=f"R-{i}", text=f"Review {i}") for i in range(5)]
    assert list(load_reviews(dump_reviews(rs))) == rs


def test_result_round_trip():
    r = SentimentResult(review_id="R-1", label=SentimentLabel.POSITIVE, score=2, confidence=0.8)
    assert result_from_dict(result_to_dict(r)) == r


def test_result_jsonl_round_trip():
    rs = [
        SentimentResult(review_id=f"R-{i}", label=SentimentLabel.POSITIVE, score=1, confidence=0.5)
        for i in range(3)
    ]
    assert list(load_results(dump_results(rs))) == rs


def test_load_skips_blank_lines():
    text = "\n\n" + dump_reviews([make_review()])
    assert len(list(load_reviews(text))) == 1
