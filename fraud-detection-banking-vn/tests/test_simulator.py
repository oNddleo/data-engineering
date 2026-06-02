"""Simulator + integration tests."""

from __future__ import annotations

import pytest

from fraudvn.engine import FraudEngine
from fraudvn.schema import Decision
from fraudvn.simulator import generate


def test_generate_reproducible_with_seed():
    a = generate(seed=42)
    b = generate(seed=42)
    assert [r.txn_id for r in a] == [r.txn_id for r in b]


def test_generate_sorted_by_time():
    txns = generate(seed=1, n_benign=20, inject_scams=["cong_an"])
    assert all(txns[i].occurred_at <= txns[i + 1].occurred_at for i in range(len(txns) - 1))


def test_benign_baseline_mostly_allowed():
    """50 random small benign txns from unique accounts → mostly ALLOW."""
    reqs = generate(seed=1, n_benign=50)
    eng = FraudEngine()
    decisions = eng.evaluate_many(reqs)
    n_allow = sum(1 for d in decisions if d.decision is Decision.ALLOW)
    # Allow most; some night-time or new-beneficiary signals can land in REVIEW.
    assert n_allow >= 40


def test_injected_cong_an_lands_in_review_or_block():
    reqs = generate(seed=1, n_benign=0, inject_scams=["cong_an"])
    eng = FraudEngine()
    decisions = eng.evaluate_many(reqs)
    cong = [d for d in decisions if "KEYWORD_CONG_AN_IMPERSONATION" in {s.name for s in d.signals}]
    assert cong
    assert all(d.decision in (Decision.REVIEW, Decision.BLOCK) for d in cong)


def test_injected_crypto_fires():
    reqs = generate(seed=1, n_benign=0, inject_scams=["crypto"])
    eng = FraudEngine()
    decisions = eng.evaluate_many(reqs)
    assert any(d.has_signal("KEYWORD_CRYPTO_FOREX_SCAM") for d in decisions)


def test_injected_chuyen_nham_fires():
    reqs = generate(seed=1, n_benign=0, inject_scams=["chuyen_nham"])
    eng = FraudEngine()
    decisions = eng.evaluate_many(reqs)
    assert any(d.has_signal("KEYWORD_WRONG_TRANSFER_SCAM") for d in decisions)


def test_injected_job_scam_fires():
    reqs = generate(seed=1, n_benign=0, inject_scams=["job_scam"])
    eng = FraudEngine()
    decisions = eng.evaluate_many(reqs)
    assert any(d.has_signal("KEYWORD_JOB_SCAM") for d in decisions)


def test_injected_loan_scam_fires():
    reqs = generate(seed=1, n_benign=0, inject_scams=["loan_scam"])
    eng = FraudEngine()
    decisions = eng.evaluate_many(reqs)
    assert any(d.has_signal("KEYWORD_LOAN_SCAM") for d in decisions)


def test_injected_blacklist_is_blocked():
    bl = ["BAD-001"]
    reqs = generate(seed=1, n_benign=0, inject_blacklist=1, blacklist=bl)
    eng = FraudEngine(blacklist=bl)
    decisions = eng.evaluate_many(reqs)
    blocked = [d for d in decisions if d.decision is Decision.BLOCK]
    assert blocked


def test_injected_velocity_fires():
    reqs = generate(seed=1, n_benign=0, inject_velocity=1)
    eng = FraudEngine()
    decisions = eng.evaluate_many(reqs)
    assert any(d.has_signal("VELOCITY_BURST") for d in decisions)


def test_injected_otp_race_fires():
    reqs = generate(seed=1, n_benign=0, inject_otp_race=1)
    eng = FraudEngine()
    decisions = eng.evaluate_many(reqs)
    assert any(d.has_signal("OTP_RACE") for d in decisions)


def test_injected_round_below_fires():
    reqs = generate(seed=1, n_benign=0, inject_round_below=1)
    eng = FraudEngine()
    decisions = eng.evaluate_many(reqs)
    assert any(d.has_signal("ROUND_AMOUNT_BELOW_10M") for d in decisions)


def test_unknown_scam_kind_raises():
    with pytest.raises(ValueError):
        generate(n_benign=0, inject_scams=["meteor"])


def test_full_mix_produces_all_decision_tiers():
    bl = ["BAD-001"]
    reqs = generate(
        seed=2,
        n_benign=20,
        inject_scams=["cong_an", "crypto"],
        inject_blacklist=1,
        inject_velocity=1,
        inject_otp_race=1,
        blacklist=bl,
    )
    eng = FraudEngine(blacklist=bl)
    decisions = eng.evaluate_many(reqs)
    tiers = {d.decision for d in decisions}
    assert Decision.BLOCK in tiers
    assert Decision.ALLOW in tiers  # benign baseline survives
