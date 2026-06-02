"""Schema validation."""

from __future__ import annotations

import pytest

from vnaddr.schema import (
    AdminLevel,
    AdminUnit,
    MatchedToken,
    MatchKind,
    ParsedAddress,
)


def test_admin_level_three_values():
    assert {x.value for x in AdminLevel} == {"PROVINCE", "DISTRICT", "WARD"}


def test_match_kind_four_values():
    assert {x.value for x in MatchKind} == {"EXACT", "FUZZY", "ABBREV", "MISSING"}


def test_admin_unit_province_no_parent_ok():
    u = AdminUnit(
        code="HCM",
        name_vi="Thành phố Hồ Chí Minh",
        name_en="Ho Chi Minh City",
        level=AdminLevel.PROVINCE,
    )
    assert u.parent_code == ""


def test_admin_unit_district_requires_parent():
    with pytest.raises(ValueError, match="must have parent_code"):
        AdminUnit(
            code="HCM:Q1",
            name_vi="Quận 1",
            name_en="District 1",
            level=AdminLevel.DISTRICT,
        )


def test_admin_unit_province_rejects_parent():
    with pytest.raises(ValueError, match="cannot have parent_code"):
        AdminUnit(
            code="HCM",
            name_vi="Thành phố Hồ Chí Minh",
            name_en="Ho Chi Minh City",
            level=AdminLevel.PROVINCE,
            parent_code="VN",
        )


def test_admin_unit_rejects_empty_code():
    with pytest.raises(ValueError, match="code"):
        AdminUnit(
            code="",
            name_vi="X",
            name_en="Y",
            level=AdminLevel.PROVINCE,
        )


def test_admin_unit_rejects_empty_name_vi():
    with pytest.raises(ValueError, match="name_vi"):
        AdminUnit(
            code="X",
            name_vi="",
            name_en="Y",
            level=AdminLevel.PROVINCE,
        )


def test_matched_token_basic():
    m = MatchedToken(
        raw_token="quan 1",
        matched_code="HCM:Q1",
        matched_name="Quận 1",
        kind=MatchKind.EXACT,
    )
    assert m.edit_distance == 0


def test_matched_token_rejects_negative_distance():
    with pytest.raises(ValueError, match="edit_distance"):
        MatchedToken(
            raw_token="x",
            matched_code="X",
            matched_name="X",
            kind=MatchKind.FUZZY,
            edit_distance=-1,
        )


def test_parsed_address_complete_property():
    p = ParsedAddress(
        raw_input="x",
        ward=MatchedToken(raw_token="", matched_code="A", matched_name="A", kind=MatchKind.EXACT),
        district=MatchedToken(
            raw_token="", matched_code="B", matched_name="B", kind=MatchKind.EXACT
        ),
        province=MatchedToken(
            raw_token="", matched_code="C", matched_name="C", kind=MatchKind.EXACT
        ),
    )
    assert p.is_complete is True
    assert p.is_partial is True


def test_parsed_address_partial():
    p = ParsedAddress(
        raw_input="x",
        province=MatchedToken(
            raw_token="", matched_code="C", matched_name="C", kind=MatchKind.EXACT
        ),
    )
    assert p.is_complete is False
    assert p.is_partial is True


def test_parsed_address_failed():
    p = ParsedAddress(raw_input="random garbage")
    assert p.is_complete is False
    assert p.is_partial is False


def test_parsed_address_normalised():
    p = ParsedAddress(
        raw_input="x",
        street="123 Le Loi",
        ward=MatchedToken(
            raw_token="", matched_code="A", matched_name="Phường 1", kind=MatchKind.EXACT
        ),
        district=MatchedToken(
            raw_token="", matched_code="B", matched_name="Quận 1", kind=MatchKind.EXACT
        ),
        province=MatchedToken(
            raw_token="", matched_code="C", matched_name="TP HCM", kind=MatchKind.EXACT
        ),
    )
    assert p.normalised == "123 Le Loi, Phường 1, Quận 1, TP HCM"
