"""Tariff rate lookups."""

from __future__ import annotations

import pytest

from vncustoms.tariff import duty_rate_for, vat_rate_for


def test_known_chapter_machinery() -> None:
    # Chapter 84 (machinery) is low-duty.
    assert duty_rate_for("84") < 0.10


def test_known_chapter_vehicles_high() -> None:
    # Chapter 87 (vehicles) has high duty.
    assert duty_rate_for("87") >= 0.20


def test_unknown_chapter_falls_back() -> None:
    """Unknown chapters should still return a plausible rate."""
    rate = duty_rate_for("06")  # live trees & flowers — not in our table
    assert 0.0 <= rate <= 1.0


def test_vat_default() -> None:
    # Chapter 85 (electronics) uses default VAT.
    assert vat_rate_for("85") == 0.08


def test_vat_reduced_essentials() -> None:
    # Chapter 03 (fish) is essential — 5% VAT.
    assert vat_rate_for("03") == 0.05


def test_vat_zero_precious_metals() -> None:
    assert vat_rate_for("71") == 0.00


@pytest.mark.parametrize("bad", ["", "8", "abc", "100"])
def test_duty_rejects_bad_chapter(bad: str) -> None:
    with pytest.raises(ValueError):
        duty_rate_for(bad)


@pytest.mark.parametrize("bad", ["", "8", "abc", "100"])
def test_vat_rejects_bad_chapter(bad: str) -> None:
    with pytest.raises(ValueError):
        vat_rate_for(bad)
