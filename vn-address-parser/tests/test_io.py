"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from vnaddr.io_jsonl import (
    dump_parsed,
    dump_units,
    load_parsed,
    load_units,
    parsed_from_dict,
    parsed_to_dict,
    unit_from_dict,
    unit_to_dict,
)
from vnaddr.parser import parse
from vnaddr.schema import AdminLevel, AdminUnit


def _province() -> AdminUnit:
    return AdminUnit(
        code="HCM",
        name_vi="Thành phố Hồ Chí Minh",
        name_en="Ho Chi Minh City",
        level=AdminLevel.PROVINCE,
    )


def _district() -> AdminUnit:
    return AdminUnit(
        code="HCM:Q1",
        name_vi="Quận 1",
        name_en="District 1",
        level=AdminLevel.DISTRICT,
        parent_code="HCM",
    )


# ---------- AdminUnit --------------------------------------------------------


def test_unit_round_trip_province():
    u = _province()
    assert unit_from_dict(unit_to_dict(u)) == u


def test_unit_round_trip_district():
    u = _district()
    assert unit_from_dict(unit_to_dict(u)) == u


def test_unit_round_trip_with_aliases():
    u = AdminUnit(
        code="HCM:Q1",
        name_vi="Quận 1",
        name_en="District 1",
        level=AdminLevel.DISTRICT,
        parent_code="HCM",
        aliases=("Q1", "Q.1"),
    )
    out = unit_from_dict(unit_to_dict(u))
    assert out.aliases == ("Q1", "Q.1")


def test_unit_dump_load_round_trip():
    units = [_province(), _district()]
    assert load_units(dump_units(units)) == units


def test_unit_load_rejects_non_object():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_units("[1, 2]\n")


# ---------- ParsedAddress ----------------------------------------------------


def test_parsed_round_trip_complete():
    p = parse("123 Lê Lợi, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh")
    assert parsed_from_dict(parsed_to_dict(p)) == p


def test_parsed_round_trip_partial():
    p = parse("Hồ Chí Minh")
    assert parsed_from_dict(parsed_to_dict(p)) == p


def test_parsed_round_trip_failure():
    p = parse("zzz xxx yyy")
    assert parsed_from_dict(parsed_to_dict(p)) == p


def test_parsed_dump_load_many():
    items = [
        parse("123 Lê Lợi, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh"),
        parse("Hồ Chí Minh"),
    ]
    assert load_parsed(dump_parsed(items)) == items


def test_parsed_dump_newline_terminated():
    p = parse("Hà Nội")
    text = dump_parsed([p])
    assert text.endswith("\n")


def test_parsed_load_rejects_non_dict_token():
    p = parse("Hà Nội")
    bad = parsed_to_dict(p)
    bad["province"] = "not a dict"
    with pytest.raises(TypeError, match="province must be dict"):
        parsed_from_dict(bad)
