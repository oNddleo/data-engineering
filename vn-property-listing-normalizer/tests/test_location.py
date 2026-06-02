"""Location parser tests."""

from __future__ import annotations

from vnprop.location import parse_district, parse_province, parse_ward


def test_parse_province_tp_hcm() -> None:
    assert "Hồ Chí Minh" in parse_province("Bán nhà tại TP. Hồ Chí Minh")


def test_parse_province_tinh() -> None:
    assert "Bình Dương" in parse_province("Tỉnh Bình Dương")


def test_parse_district_numeric() -> None:
    assert parse_district("Quận 1") == "Quận 1"


def test_parse_district_named() -> None:
    assert "Cầu Giấy" in parse_district("Quận Cầu Giấy, Hà Nội")


def test_parse_district_abbr() -> None:
    assert parse_district("Q.7").startswith("Quận")


def test_parse_ward_numeric() -> None:
    assert parse_ward("Phường 5") == "Phường 5"


def test_parse_ward_named() -> None:
    assert "Thảo Điền" in parse_ward("Phường Thảo Điền")


def test_no_location_returns_empty() -> None:
    assert parse_province("nothing here") == ""
    assert parse_district("nothing here") == ""
    assert parse_ward("nothing here") == ""
