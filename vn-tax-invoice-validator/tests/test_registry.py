"""Tax registry — lookup behaviour."""

from __future__ import annotations

from vntax.registry import InMemoryRegistry, TaxEntity


def test_lookup_vietcombank_seed():
    r = InMemoryRegistry()
    hit = r.lookup("0100109106")
    assert hit is not None
    assert hit.name == "Vietcombank"
    assert hit.status == "ACTIVE"


def test_lookup_unknown_mst_returns_none():
    r = InMemoryRegistry()
    assert r.lookup("9999999999") is None


def test_lookup_13_digit_falls_back_to_primary():
    """An unregistered branch suffix on a known primary still resolves."""
    r = InMemoryRegistry()
    # FPT primary is 0301442379; branch 999 isn't separately seeded.
    hit = r.lookup("0301442379999")
    assert hit is not None
    assert hit.name == "Công ty CP FPT"


def test_lookup_returns_specific_branch_when_seeded():
    """A specifically-registered branch wins over the 10-digit fallback."""
    r = InMemoryRegistry()
    r.add(
        TaxEntity(
            mst="0100109106001",
            name="Vietcombank — Hanoi HQ",
            address="Hanoi",
            status="ACTIVE",
            registered_at="1993-04-01",
        )
    )
    hit = r.lookup("0100109106001")
    assert hit is not None
    assert hit.name == "Vietcombank — Hanoi HQ"


def test_lookup_suspended_status_returned():
    r = InMemoryRegistry()
    hit = r.lookup("0102156359")
    assert hit is not None
    assert hit.status == "SUSPENDED"


def test_custom_registry_with_empty_seed():
    r = InMemoryRegistry(entities=[])
    assert r.lookup("0100109106") is None


def test_custom_registry_with_custom_entities():
    seed = [
        TaxEntity(
            mst="1234567894",
            name="Custom Co",
            address="—",
            status="ACTIVE",
            registered_at="2026-01-01",
        ),
    ]
    r = InMemoryRegistry(entities=seed)
    hit = r.lookup("1234567894")
    assert hit is not None
    assert hit.name == "Custom Co"


def test_add_replaces_existing():
    r = InMemoryRegistry()
    r.add(
        TaxEntity(
            mst="0100109106",
            name="OVERRIDE",
            address="—",
            status="CLOSED",
            registered_at="2026-01-01",
        )
    )
    hit = r.lookup("0100109106")
    assert hit is not None
    assert hit.name == "OVERRIDE"
    assert hit.status == "CLOSED"
