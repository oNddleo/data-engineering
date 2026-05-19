"""Bundled hub + courier directories."""

from __future__ import annotations

import pytest

from vnpost.couriers import all_profiles, profile, sla_hours
from vnpost.hubs import all_hubs, by_city, by_code, gateways
from vnpost.schema import CourierCode

# ---------- hubs -------------------------------------------------------------


def test_hubs_bundled_count():
    """Expect 16 hubs (HCM 5, HN 4, DN 2, HP 2, CT 2 + national SC)."""
    assert len(all_hubs()) == 16


def test_hubs_include_hcm_central():
    codes = {h.code for h in all_hubs()}
    assert "HCM-TPN" in codes
    assert "HCM-TD" in codes


def test_by_city_hcm_count():
    hcm = by_city("HCM")
    assert len(hcm) == 5


def test_by_code_lookup():
    h = by_code("HN-CG")
    assert h is not None
    assert h.name_vi == "Kho Cầu Giấy"


def test_by_code_unknown_returns_none():
    assert by_code("XX-NONE") is None


def test_gateways_marked():
    """Each city should have at least one gateway hub."""
    gw_cities = {g.city for g in gateways()}
    for city in ("HCM", "HN", "DN", "HP", "CT"):
        assert city in gw_cities


# ---------- couriers ---------------------------------------------------------


def test_courier_profiles_complete():
    assert len(all_profiles()) == 5
    codes = {p.code for p in all_profiles()}
    assert codes == set(CourierCode)


def test_profile_lookup():
    p = profile(CourierCode.GHN)
    assert p.name_en == "GiaoHangNhanh"
    assert p.sla_same_city_hours == 24


def test_sla_hours_intra_city():
    """Same-city SLA < inter-city SLA for every courier."""
    for code in CourierCode:
        same = sla_hours(code, origin_city="HCM", dest_city="HCM")
        inter = sla_hours(code, origin_city="HCM", dest_city="HN")
        assert same < inter


def test_sla_hours_unknown_courier_raises_via_profile():
    """profile() returns the bundled profile or raises KeyError."""
    with pytest.raises(KeyError):
        profile("XX")  # type: ignore[arg-type]
