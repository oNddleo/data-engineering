"""BlacklistRule tests."""

from __future__ import annotations

from n247mon.alerts import AlertKind, Severity
from n247mon.rules import BlacklistRule

from ._fixtures import make_txn


def test_blacklist_hit_fires():
    rule = BlacklistRule({"BAD-001", "BAD-002"})
    alerts = rule.consume(make_txn(beneficiary="BAD-001"))
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.BLACKLIST_HIT
    assert alerts[0].severity is Severity.CRIT


def test_blacklist_miss_no_alert():
    rule = BlacklistRule({"BAD-001"})
    assert rule.consume(make_txn(beneficiary="GOOD-001")) == []


def test_blacklist_empty_set_never_fires():
    rule = BlacklistRule(set())
    assert rule.consume(make_txn(beneficiary="ANY-ACCOUNT")) == []


def test_blacklist_strips_whitespace_on_load():
    rule = BlacklistRule({"  BAD-001  ", "", "  "})
    assert rule.size == 1
    assert rule.consume(make_txn(beneficiary="BAD-001")) != []


def test_blacklist_size_property():
    rule = BlacklistRule({"a", "b", "c"})
    assert rule.size == 3


def test_blacklist_alert_carries_beneficiary_in_detail():
    rule = BlacklistRule({"BAD-XYZ"})
    alerts = rule.consume(make_txn(beneficiary="BAD-XYZ", beneficiary_bin="970418"))
    assert "BAD-XYZ" in alerts[0].detail
    assert "970418" in alerts[0].detail
