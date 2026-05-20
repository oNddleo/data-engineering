"""Area parser tests."""

from __future__ import annotations

import pytest

from vnprop.area import parse_area_m2


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("75 m2", 75),
        ("75m²", 75),
        ("75.5m²", 76),  # ceil
        ("75,5 m2", 76),
        ("7x10m", 70),
        ("Diện tích 80m²", 80),
        ("100m", 100),
    ],
)
def test_parse_area(text: str, expected: int) -> None:
    assert parse_area_m2(text) == expected


def test_parse_area_rejects_empty() -> None:
    with pytest.raises(ValueError):
        parse_area_m2("")


def test_parse_area_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_area_m2("không có diện tích")
