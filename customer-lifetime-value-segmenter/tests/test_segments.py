"""Segment classification + transitions."""

from __future__ import annotations

import pytest

from clvseg.schema import Segment
from clvseg.segments import (
    classify_all,
    rfm_to_segment,
    segment_distribution,
    top_in_segment,
    transitions,
)

from ._fixtures import make_score


def test_555_is_champions():
    assert rfm_to_segment(5, 5, 5) is Segment.CHAMPIONS


def test_511_is_new_customers():
    """R=5, F=1, M=any → recent buyer with low historical frequency."""
    assert rfm_to_segment(5, 1, 1) is Segment.NEW_CUSTOMERS
    assert rfm_to_segment(5, 2, 3) is Segment.NEW_CUSTOMERS


def test_543_is_loyal():
    assert rfm_to_segment(5, 4, 3) is Segment.LOYAL_CUSTOMERS


def test_153_is_cant_lose():
    """R=1, F=5 → was a top buyer, hasn't bought in ages — escalation."""
    assert rfm_to_segment(1, 5, 3) is Segment.CANT_LOSE_THEM


def test_145_is_at_risk():
    assert rfm_to_segment(1, 4, 5) is Segment.AT_RISK


def test_111_is_lost():
    assert rfm_to_segment(1, 1, 1) is Segment.LOST


def test_112_still_lost_when_f_is_1():
    """F=1 with R=1 is LOST regardless of M."""
    assert rfm_to_segment(1, 1, 5) is Segment.LOST


def test_validates_score_range():
    with pytest.raises(ValueError):
        rfm_to_segment(0, 3, 3)
    with pytest.raises(ValueError):
        rfm_to_segment(3, 6, 3)


def test_classify_all_builds_assignment_map():
    scores = [
        make_score(customer_id="C-1", r_score=5, f_score=5, m_score=5),
        make_score(customer_id="C-2", r_score=1, f_score=1, m_score=1),
    ]
    out = classify_all(scores)
    assert out["C-1"] is Segment.CHAMPIONS
    assert out["C-2"] is Segment.LOST


def test_distribution_zero_fills():
    """Every segment appears in the output, even with count 0."""
    assignments = {"C-1": Segment.CHAMPIONS}
    dist = segment_distribution(assignments)
    assert dist[Segment.CHAMPIONS] == 1
    assert dist[Segment.LOST] == 0
    assert set(dist) == set(Segment)


def test_top_in_segment_orders_by_monetary_desc():
    scores = [
        make_score(customer_id="C-1", r_score=5, f_score=5, m_score=5, monetary_vnd=1_000_000),
        make_score(customer_id="C-2", r_score=5, f_score=5, m_score=5, monetary_vnd=3_000_000),
        make_score(customer_id="C-3", r_score=5, f_score=5, m_score=5, monetary_vnd=2_000_000),
    ]
    assignments = classify_all(scores)
    top = top_in_segment(scores, assignments, Segment.CHAMPIONS, n=10)
    assert [s.customer_id for s in top] == ["C-2", "C-3", "C-1"]


def test_top_in_segment_ties_broken_by_recency_then_id():
    scores = [
        make_score(
            customer_id="C-B",
            r_score=5,
            f_score=5,
            m_score=5,
            monetary_vnd=1_000_000,
            recency_days=10,
        ),
        make_score(
            customer_id="C-A",
            r_score=5,
            f_score=5,
            m_score=5,
            monetary_vnd=1_000_000,
            recency_days=5,
        ),
        make_score(
            customer_id="C-C",
            r_score=5,
            f_score=5,
            m_score=5,
            monetary_vnd=1_000_000,
            recency_days=10,
        ),
    ]
    assignments = classify_all(scores)
    top = top_in_segment(scores, assignments, Segment.CHAMPIONS, n=3)
    # Same monetary → recency ascending → C-A first; then C-B / C-C alphabetical.
    assert [s.customer_id for s in top] == ["C-A", "C-B", "C-C"]


def test_top_in_segment_validates_n():
    with pytest.raises(ValueError):
        top_in_segment([], {}, Segment.CHAMPIONS, n=0)


def test_transitions_counts_movements():
    before = {"C-1": Segment.NEW_CUSTOMERS, "C-2": Segment.LOYAL_CUSTOMERS}
    after = {"C-1": Segment.LOYAL_CUSTOMERS, "C-2": Segment.LOYAL_CUSTOMERS}
    t = transitions(before, after)
    assert t[(Segment.NEW_CUSTOMERS, Segment.LOYAL_CUSTOMERS)] == 1
    assert t[(Segment.LOYAL_CUSTOMERS, Segment.LOYAL_CUSTOMERS)] == 1


def test_transitions_skips_new_acquisitions():
    """A customer in ``after`` but not ``before`` is a new acquisition — not a transition."""
    before = {"C-1": Segment.LOYAL_CUSTOMERS}
    after = {"C-1": Segment.LOYAL_CUSTOMERS, "C-NEW": Segment.NEW_CUSTOMERS}
    t = transitions(before, after)
    assert (Segment.LOYAL_CUSTOMERS, Segment.LOYAL_CUSTOMERS) in t
    # C-NEW doesn't appear since it has no ``before`` segment.
    assert sum(t.values()) == 1


def test_transitions_skips_churn():
    """A customer in ``before`` but not ``after`` (churned record) is also skipped."""
    before = {"C-1": Segment.LOYAL_CUSTOMERS, "C-2": Segment.CHAMPIONS}
    after = {"C-1": Segment.LOYAL_CUSTOMERS}
    t = transitions(before, after)
    assert sum(t.values()) == 1


def test_top_in_segment_empty_segment_returns_empty():
    scores = [make_score(r_score=5, f_score=5, m_score=5)]
    assignments = classify_all(scores)
    assert top_in_segment(scores, assignments, Segment.LOST, n=5) == []
