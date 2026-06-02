"""Alert / Severity enum tests."""

from __future__ import annotations

from n247mon.alerts import Alert, AlertKind, Severity


def test_severity_ordering_is_string():
    # We use str-Enum so Alert serialises naturally — verify identity.
    assert Severity.INFO.value == "INFO"
    assert Severity.WARN.value == "WARN"
    assert Severity.CRIT.value == "CRIT"


def test_alert_kind_count():
    # Make sure no rules silently drop / add kinds.
    assert {k.value for k in AlertKind} == {
        "BIO_REQUIRED_SINGLE_TXN",
        "BIO_REQUIRED_CUMULATIVE",
        "VELOCITY_SPIKE",
        "STRUCTURING_SUSPECTED",
        "BLACKLIST_HIT",
    }


def test_alert_frozen():
    a = Alert(
        kind=AlertKind.BLACKLIST_HIT,
        severity=Severity.CRIT,
        txn_id="T-1",
        account="A1",
        detail="hit",
        amount_vnd=1_000_000,
    )
    import pytest

    with pytest.raises((AttributeError, TypeError)):
        a.amount_vnd = 999  # type: ignore[misc]
