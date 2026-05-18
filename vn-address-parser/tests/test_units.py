"""Bundled directory coverage."""

from __future__ import annotations

from vnaddr.schema import AdminLevel
from vnaddr.units import all_units, by_code, by_level, by_parent, n_provinces


def test_n_provinces_is_63():
    assert n_provinces() == 63


def test_all_units_includes_hcm():
    codes = {u.code for u in all_units()}
    assert "HCM" in codes


def test_all_units_includes_hcm_districts():
    codes = {u.code for u in all_units()}
    assert "HCM:Q1" in codes
    assert "HCM:BT" in codes
    assert "HCM:TD" in codes


def test_by_level_province_count():
    provinces = by_level(AdminLevel.PROVINCE)
    assert len(provinces) == 63


def test_by_level_district_count():
    """22 HCM + 12 HN + 6 DN = 40 districts."""
    districts = by_level(AdminLevel.DISTRICT)
    assert len(districts) == 22 + 12 + 6


def test_by_code_lookup():
    u = by_code("HCM:Q1")
    assert u is not None
    assert u.name_vi == "Quận 1"


def test_by_code_unknown_returns_none():
    assert by_code("XX:YYY") is None


def test_by_parent_hcm_returns_22_districts():
    children = by_parent("HCM")
    assert len(children) == 22


def test_by_parent_q1_returns_wards():
    children = by_parent("HCM:Q1")
    assert len(children) >= 3
    assert any(c.name_vi == "Phường Bến Nghé" for c in children)


def test_admin_codes_are_unique():
    codes = [u.code for u in all_units()]
    assert len(codes) == len(set(codes))


def test_all_districts_have_valid_parent():
    province_codes = {u.code for u in by_level(AdminLevel.PROVINCE)}
    for d in by_level(AdminLevel.DISTRICT):
        assert d.parent_code in province_codes


def test_all_wards_have_valid_parent():
    district_codes = {u.code for u in by_level(AdminLevel.DISTRICT)}
    for w in by_level(AdminLevel.WARD):
        assert w.parent_code in district_codes
