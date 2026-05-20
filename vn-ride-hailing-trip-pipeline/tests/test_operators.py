"""Operator + city directory."""

from __future__ import annotations

import pytest

from vnride.operators import (
    all_cities,
    all_operators,
    city_for,
    commission_bps,
    operator_for,
)


def test_directory_has_four_operators() -> None:
    assert len(all_operators()) == 4


def test_directory_has_six_cities() -> None:
    assert len(all_cities()) == 6


def test_market_shares_sum_reasonably() -> None:
    """Bundled share should be 90-105% (we cover the four active platforms)."""
    total = sum(o.market_share_pct for o in all_operators())
    assert 90.0 <= total <= 105.0


@pytest.mark.parametrize("abbr", ["GRAB", "BE", "XANHSM", "MAXIM"])
def test_operator_lookup(abbr: str) -> None:
    op = operator_for(abbr)
    assert op is not None
    assert op.abbreviation == abbr


def test_operator_lookup_case_insensitive() -> None:
    assert operator_for("grab") is not None
    assert operator_for("Grab") is not None


def test_operator_lookup_unknown() -> None:
    assert operator_for("UBER") is None


@pytest.mark.parametrize("code", ["SGN", "HAN", "DAD", "HPH", "CTH", "NHA"])
def test_city_lookup(code: str) -> None:
    c = city_for(code)
    assert c is not None
    assert c.code == code


def test_city_lookup_case_insensitive() -> None:
    assert city_for("sgn") is not None


def test_city_lookup_unknown() -> None:
    assert city_for("XXX") is None


def test_commission_bps_grab_car() -> None:
    assert commission_bps("GRAB", "CAR") == 2_500


def test_commission_bps_grab_bike() -> None:
    assert commission_bps("GRAB", "BIKE") == 2_000


def test_commission_bps_unknown_operator() -> None:
    with pytest.raises(ValueError, match="operator"):
        commission_bps("UBER", "CAR")


def test_commission_bps_unknown_service() -> None:
    with pytest.raises(ValueError, match="service"):
        commission_bps("GRAB", "TRAIN")


def test_all_abbreviations_unique() -> None:
    abbrs = [o.abbreviation for o in all_operators()]
    assert len(abbrs) == len(set(abbrs))


def test_all_city_codes_unique() -> None:
    codes = [c.code for c in all_cities()]
    assert len(codes) == len(set(codes))


def test_commission_in_bps_range() -> None:
    """All commissions are within [0, 10_000] bps."""
    for op in all_operators():
        for val in (
            op.commission_car_bps,
            op.commission_bike_bps,
            op.commission_delivery_bps,
        ):
            assert 0 <= val <= 10_000


def test_grab_is_largest() -> None:
    """Sanity check — Grab has the largest market share."""
    ops_by_share = sorted(
        all_operators(),
        key=lambda o: o.market_share_pct,
        reverse=True,
    )
    assert ops_by_share[0].abbreviation == "GRAB"
