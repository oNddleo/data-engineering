"""NAPAS routing: rail selection + fee computation."""

from __future__ import annotations

import pytest

from vnbank.routing import NAPAS_247_MAX_VND, Rail, route


def test_route_same_bank_is_intra() -> None:
    d = route("970436", "970436", 100_000)
    assert d.rail is Rail.INTRA_BANK
    assert d.fee_vnd == 0


def test_route_different_banks_small_amount_napas() -> None:
    d = route("970436", "970418", 500_000)
    assert d.rail is Rail.NAPAS_247
    assert d.fee_vnd == 0  # < 1M VND → free at most banks


def test_route_napas_fee_above_one_million() -> None:
    d = route("970436", "970418", 5_000_000)
    assert d.rail is Rail.NAPAS_247
    assert d.fee_vnd == 5_000  # flat fee tier


def test_route_napas_max() -> None:
    """Exactly at the NAPAS-247 cap routes via NAPAS."""
    d = route("970436", "970418", NAPAS_247_MAX_VND)
    assert d.rail is Rail.NAPAS_247


def test_route_above_napas_max_uses_citad() -> None:
    d = route("970436", "970418", NAPAS_247_MAX_VND + 1)
    assert d.rail is Rail.CITAD
    assert d.fee_vnd >= 20_000


def test_route_citad_fee_capped() -> None:
    """Citad fee caps at 1,000,000 VND for huge amounts."""
    d = route("970436", "970418", 100_000_000_000)
    assert d.rail is Rail.CITAD
    assert d.fee_vnd == 1_000_000


def test_route_rejects_unknown_sender() -> None:
    with pytest.raises(ValueError, match="sender"):
        route("999999", "970436", 100_000)


def test_route_rejects_unknown_receiver() -> None:
    with pytest.raises(ValueError, match="receiver"):
        route("970436", "999999", 100_000)


def test_route_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="amount_vnd"):
        route("970436", "970418", -1)


def test_route_zero_amount_intra_is_free() -> None:
    d = route("970436", "970436", 0)
    assert d.rail is Rail.INTRA_BANK
    assert d.fee_vnd == 0


def test_napas_247_max_is_500m() -> None:
    """Sanity check — value updated 2024-07-01 per SBV 1085/QĐ-NHNN."""
    assert NAPAS_247_MAX_VND == 500_000_000
