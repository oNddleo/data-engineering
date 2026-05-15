"""State store tests."""

from __future__ import annotations

from fraudvn.state import AccountState, StateStore

from ._fixtures import make_req


def test_empty_store():
    s = StateStore()
    assert len(s) == 0


def test_get_creates_state_lazily():
    s = StateStore()
    a = s.get("ACC-A")
    assert isinstance(a, AccountState)
    assert a.account_id == "ACC-A"
    assert len(s) == 1


def test_get_returns_same_object_twice():
    s = StateStore()
    a1 = s.get("ACC-A")
    a2 = s.get("ACC-A")
    assert a1 is a2


def test_record_adds_to_prior_beneficiaries():
    s = StateStore()
    s.record(make_req(initiator="A", beneficiary="B"))
    assert "B" in s.get("A").prior_beneficiaries


def test_record_adds_to_recent_outgoing():
    s = StateStore()
    s.record(make_req(initiator="A", beneficiary="B"))
    assert len(s.get("A").recent_outgoing) == 1


def test_record_adds_to_dst_incoming_sources():
    s = StateStore()
    s.record(make_req(initiator="A", beneficiary="B"))
    assert any(src == "A" for src, _ in s.get("B").recent_incoming_sources)


def test_account_ids_after_record():
    s = StateStore()
    s.record(make_req(initiator="A", beneficiary="B"))
    s.record(make_req(initiator="C", beneficiary="B"))
    assert s.all_account_ids() == {"A", "B", "C"}


def test_recent_outgoing_bounded_maxlen():
    s = StateStore()
    a = s.get("A")
    assert a.recent_outgoing.maxlen == 200
