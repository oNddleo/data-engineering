"""End-to-end engine + decision-tier tests."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from fraudvn.engine import BLOCK_THRESHOLD, REVIEW_THRESHOLD, FraudEngine, score_to_decision
from fraudvn.schema import VN_TZ, Decision

from ._fixtures import make_req, t_at


def test_score_to_decision_tiers():
    assert score_to_decision(0) is Decision.ALLOW
    assert score_to_decision(REVIEW_THRESHOLD - 1) is Decision.ALLOW
    assert score_to_decision(REVIEW_THRESHOLD) is Decision.REVIEW
    assert score_to_decision(BLOCK_THRESHOLD - 1) is Decision.REVIEW
    assert score_to_decision(BLOCK_THRESHOLD) is Decision.BLOCK
    assert score_to_decision(500) is Decision.BLOCK


def test_engine_rejects_inverted_thresholds():
    with pytest.raises(ValueError):
        FraudEngine(review_threshold=100, block_threshold=50)


def test_clean_txn_allowed():
    eng = FraudEngine()
    d = eng.evaluate(make_req(amount=500_000, narrative="an trua"))
    assert d.decision is Decision.ALLOW
    assert d.score == 0


def test_keyword_cong_an_alone_triggers_review():
    """CONG_AN_IMPERSONATION is 55 points — above REVIEW (50) but below BLOCK (100)."""
    eng = FraudEngine()
    d = eng.evaluate(make_req(narrative="Yêu cầu Công An điều tra chuyển khoản"))
    assert d.decision is Decision.REVIEW
    assert d.score >= 55


def test_blacklist_alone_blocks():
    eng = FraudEngine(blacklist={"BAD-001"})
    d = eng.evaluate(make_req(beneficiary="BAD-001", narrative="an trua"))
    assert d.decision is Decision.BLOCK


def test_state_updates_after_evaluate():
    eng = FraudEngine()
    eng.evaluate(make_req(initiator="A", beneficiary="B"))
    assert "B" in eng.state.get("A").prior_beneficiaries


def test_repeat_beneficiary_does_not_fire_new_beneficiary():
    """Second large txn to same beneficiary shouldn't trigger NEW_BENEFICIARY_LARGE."""
    eng = FraudEngine()
    eng.evaluate(
        make_req(txn_id="T-1", initiator="A", beneficiary="B", amount=6_000_000, narrative="abc")
    )
    d2 = eng.evaluate(
        make_req(
            txn_id="T-2",
            initiator="A",
            beneficiary="B",
            amount=6_000_000,
            narrative="abc",
            occurred_at=t_at(60),
        )
    )
    assert not d2.has_signal("NEW_BENEFICIARY_LARGE")


def test_signals_sorted_by_points_desc():
    eng = FraudEngine(blacklist={"BAD-001"})
    d = eng.evaluate(
        make_req(
            beneficiary="BAD-001",
            narrative="Đầu tư crypto",
            amount=9_900_000,
        )
    )
    pts = [s.points for s in d.signals]
    assert pts == sorted(pts, reverse=True)


def test_latency_field_populated_and_small():
    eng = FraudEngine()
    d = eng.evaluate(make_req(narrative="an trua"))
    # The < 200ms budget — but in tests, latency should be well under 50ms.
    assert 0 < d.latency_ms < 200


def test_blacklist_review_threshold_combined_to_block():
    """A 55-point KEYWORD hit + a 25-point NEW_BENEFICIARY_LARGE crosses 100? No, 80 → REVIEW.
    Stack 3 signals: keyword (55) + new_beneficiary (25) + round_below (15) = 95 → REVIEW.
    Add OTP race (35) → 130 → BLOCK.
    """
    eng = FraudEngine()
    d = eng.evaluate(
        make_req(
            narrative="Yêu cầu Công An điều tra",
            amount=9_800_000,
            otp_delta_seconds=2.0,
        )
    )
    assert d.decision is Decision.BLOCK


def test_velocity_burst_after_six_txns():
    eng = FraudEngine()
    base = datetime(2026, 5, 14, 14, 0, tzinfo=VN_TZ)
    # First 5 — don't trigger velocity yet.
    for i in range(5):
        eng.evaluate(
            make_req(
                txn_id=f"T-{i}",
                initiator="A",
                beneficiary=f"B-{i}",
                amount=500_000,
                narrative="x",
                occurred_at=base + timedelta(seconds=i * 30),
            )
        )
    # 6th should trigger VELOCITY_BURST.
    d = eng.evaluate(
        make_req(
            txn_id="T-6",
            initiator="A",
            beneficiary="B-NEW",
            amount=500_000,
            narrative="x",
            occurred_at=base + timedelta(seconds=180),
        )
    )
    assert d.has_signal("VELOCITY_BURST")


def test_beneficiary_hot_after_five_distinct_sources():
    eng = FraudEngine()
    base = datetime(2026, 5, 14, 14, 0, tzinfo=VN_TZ)
    # 5 distinct sources fund D first; the 6th attempt to D should trigger HOT.
    for i in range(5):
        eng.evaluate(
            make_req(
                txn_id=f"T-{i}",
                initiator=f"S-{i}",
                beneficiary="D",
                amount=500_000,
                narrative="x",
                occurred_at=base + timedelta(seconds=i * 60),
            )
        )
    d = eng.evaluate(
        make_req(
            txn_id="T-6",
            initiator="S-NEW",
            beneficiary="D",
            amount=500_000,
            narrative="x",
            occurred_at=base + timedelta(seconds=400),
        )
    )
    assert d.has_signal("BENEFICIARY_HOT")


def test_evaluate_many_returns_in_order():
    eng = FraudEngine()
    reqs = [make_req(txn_id=f"T-{i}", occurred_at=t_at(i)) for i in range(5)]
    decisions = eng.evaluate_many(reqs)
    assert [d.txn_id for d in decisions] == [f"T-{i}" for i in range(5)]


def test_engine_state_visible_via_property():
    eng = FraudEngine()
    assert len(eng.state) == 0
    eng.evaluate(make_req())
    assert len(eng.state) >= 2  # initiator + beneficiary


def test_blacklist_size_property():
    eng = FraudEngine(blacklist={"A", "B", "C"})
    assert eng.blacklist_size == 3
