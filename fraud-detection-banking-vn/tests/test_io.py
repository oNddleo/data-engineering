"""JSONL codec tests."""

from __future__ import annotations

from fraudvn.io_jsonl import (
    decision_from_dict,
    decision_to_dict,
    dump_decisions,
    dump_requests,
    load_decisions,
    load_requests,
    req_from_dict,
    req_to_dict,
)
from fraudvn.schema import Decision, FraudDecision, SignalHit

from ._fixtures import make_req


def test_req_round_trip_no_otp():
    r = make_req(amount=12_345_678)
    assert req_from_dict(req_to_dict(r)) == r


def test_req_round_trip_with_otp():
    r = make_req(otp_delta_seconds=3.5)
    assert req_from_dict(req_to_dict(r)) == r


def test_dump_load_requests():
    reqs = [make_req(txn_id=f"T-{i}", amount=1_000 + i) for i in range(5)]
    loaded = list(load_requests(dump_requests(reqs)))
    assert loaded == reqs


def test_decision_round_trip():
    d = FraudDecision(
        txn_id="T-1",
        decision=Decision.REVIEW,
        score=60,
        signals=(SignalHit(name="A", points=30, detail="x"),),
        latency_ms=1.23,
    )
    assert decision_from_dict(decision_to_dict(d)) == d


def test_dump_load_decisions():
    decisions = [
        FraudDecision(txn_id=f"T-{i}", decision=Decision.ALLOW, score=0, signals=(), latency_ms=0.5)
        for i in range(3)
    ]
    loaded = list(load_decisions(dump_decisions(decisions)))
    assert loaded == decisions


def test_load_skips_blank_lines():
    text = "\n\n" + dump_requests([make_req()])
    assert len(list(load_requests(text))) == 1
