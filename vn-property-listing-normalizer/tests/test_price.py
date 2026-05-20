"""Price parser tests."""

from __future__ import annotations

import pytest

from vnprop.price import format_price_vnd, parse_price_vnd


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2 tỷ", 2_000_000_000),
        ("2.5 tỷ", 2_500_000_000),
        ("3,2 tỷ", 3_200_000_000),
        ("850 triệu", 850_000_000),
        ("850tr", 850_000_000),
        ("50tr/m²", 50_000_000),
        ("5.500.000.000", 5_500_000_000),
        ("100k", 100_000),
        ("100 vnd", 100),
    ],
)
def test_parse_price(text: str, expected: int) -> None:
    assert parse_price_vnd(text) == expected


def test_parse_price_rejects_empty() -> None:
    with pytest.raises(ValueError):
        parse_price_vnd("")


def test_parse_price_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_price_vnd("xyz")


def test_format_price_billions() -> None:
    assert format_price_vnd(2_500_000_000) == "2.50 tỷ"


def test_format_price_millions() -> None:
    assert format_price_vnd(850_000_000) == "850 triệu"


def test_format_price_small() -> None:
    assert "VND" in format_price_vnd(100)


def test_format_rejects_negative() -> None:
    with pytest.raises(ValueError):
        format_price_vnd(-1)
