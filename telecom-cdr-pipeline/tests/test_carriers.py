"""Carrier directory: prefix resolution + MSISDN normalisation."""

from __future__ import annotations

import pytest

from cdrpipe.carriers import (
    all_profiles,
    carrier_for,
    is_premium_msisdn,
    normalise_msisdn,
    profile_for,
)
from cdrpipe.schema import Carrier

# ---------- normalise_msisdn ------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0961234567", "0961234567"),
        ("+84961234567", "0961234567"),
        ("84961234567", "0961234567"),
        ("961234567", "0961234567"),
        ("+84 96 123 4567", "0961234567"),
        ("096-123-4567", "0961234567"),
    ],
)
def test_normalise_msisdn_forms(raw: str, expected: str) -> None:
    assert normalise_msisdn(raw) == expected


def test_normalise_msisdn_passthrough_garbage() -> None:
    """A non-VN-looking string of the wrong length is returned unchanged."""
    assert normalise_msisdn("nope") == "nope"


# ---------- carrier_for -----------------------------------------------------


@pytest.mark.parametrize(
    ("msisdn", "carrier"),
    [
        ("0961234567", Carrier.VIETTEL),
        ("0971234567", Carrier.VIETTEL),
        ("0981234567", Carrier.VIETTEL),
        ("0861234567", Carrier.VIETTEL),
        ("0321234567", Carrier.VIETTEL),
        ("0391234567", Carrier.VIETTEL),
        ("0911234567", Carrier.VINAPHONE),
        ("0941234567", Carrier.VINAPHONE),
        ("0811234567", Carrier.VINAPHONE),
        ("0901234567", Carrier.MOBIFONE),
        ("0931234567", Carrier.MOBIFONE),
        ("0701234567", Carrier.MOBIFONE),
        ("0921234567", Carrier.VIETNAMOBILE),
        ("0561234567", Carrier.VIETNAMOBILE),
        ("0551234567", Carrier.REDDI),
        ("0591234567", Carrier.REDDI),
    ],
)
def test_carrier_for_resolves_all_five(msisdn: str, carrier: Carrier) -> None:
    assert carrier_for(msisdn) is carrier


def test_carrier_for_e164() -> None:
    """+84 form should resolve identically to 0X form."""
    assert carrier_for("+84961234567") is Carrier.VIETTEL


def test_carrier_for_unknown_returns_unknown() -> None:
    assert carrier_for("0001234567") is Carrier.UNKNOWN


def test_carrier_for_too_short_returns_unknown() -> None:
    assert carrier_for("123") is Carrier.UNKNOWN


def test_carrier_for_foreign_returns_unknown() -> None:
    assert carrier_for("+1 415 555 0100") is Carrier.UNKNOWN


# ---------- is_premium_msisdn -----------------------------------------------


@pytest.mark.parametrize(
    "msisdn",
    ["1900123456", "1800999", "1900000000", "8100", "8999", "8"],
)
def test_is_premium_msisdn_detects(msisdn: str) -> None:
    assert is_premium_msisdn(msisdn) is True


@pytest.mark.parametrize(
    "msisdn",
    ["0961234567", "0911234567", "0901234567", "1234567890"],
)
def test_is_premium_msisdn_rejects_normal(msisdn: str) -> None:
    assert is_premium_msisdn(msisdn) is False


# ---------- profile_for / all_profiles --------------------------------------


def test_all_profiles_returns_five() -> None:
    assert len(all_profiles()) == 5


def test_all_profiles_market_share_reasonable() -> None:
    """Total market share should be near 100% (with rounding)."""
    total = sum(p.market_share_pct for p in all_profiles())
    assert 95.0 <= total <= 105.0


def test_profile_for_viettel() -> None:
    p = profile_for(Carrier.VIETTEL)
    assert p is not None
    assert p.code is Carrier.VIETTEL
    assert "096" in p.prefixes


def test_profile_for_unknown_returns_none() -> None:
    assert profile_for(Carrier.UNKNOWN) is None


def test_prefixes_are_disjoint() -> None:
    """No two carriers share a prefix."""
    seen: dict[str, Carrier] = {}
    for p in all_profiles():
        for prefix in p.prefixes:
            assert (
                prefix not in seen
            ), f"prefix {prefix} claimed by both {seen[prefix]} and {p.code}"
            seen[prefix] = p.code
