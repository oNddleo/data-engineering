"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from fraudvn.engine import BLOCK_THRESHOLD, REVIEW_THRESHOLD, FraudEngine, score_to_decision
from fraudvn.io_jsonl import req_from_dict, req_to_dict
from fraudvn.keywords import normalize_vn_text
from fraudvn.schema import Decision

from ._fixtures import make_req


@given(score=st.integers(min_value=0, max_value=10_000))
def test_score_to_decision_is_total(score):
    """Property: every non-negative integer maps to one of three tiers."""
    assert score_to_decision(score) in (Decision.ALLOW, Decision.REVIEW, Decision.BLOCK)


@given(score=st.integers(min_value=BLOCK_THRESHOLD, max_value=10_000))
def test_score_above_block_threshold_always_blocks(score):
    assert score_to_decision(score) is Decision.BLOCK


@given(score=st.integers(min_value=0, max_value=REVIEW_THRESHOLD - 1))
def test_score_below_review_threshold_always_allows(score):
    assert score_to_decision(score) is Decision.ALLOW


@given(amount=st.integers(min_value=1, max_value=10**11))
def test_req_round_trips_through_jsonl(amount):
    r = make_req(amount=amount)
    assert req_from_dict(req_to_dict(r)) == r


@given(text=st.text(min_size=0, max_size=100))
def test_normalize_vn_text_idempotent(text):
    """Property: normalize(normalize(x)) == normalize(x)."""
    once = normalize_vn_text(text)
    twice = normalize_vn_text(once)
    assert once == twice


def test_clean_short_narrative_always_allow():
    """Property-ish: a clean narrative + small amount + day-time → ALLOW."""
    eng = FraudEngine()
    d = eng.evaluate(make_req(amount=500_000, narrative="thanh toan tien dien"))
    assert d.decision is Decision.ALLOW
