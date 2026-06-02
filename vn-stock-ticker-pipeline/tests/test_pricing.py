"""Price-band / tick-size / lot-size validators."""

from __future__ import annotations

import pytest

from vnstock.pricing import (
    ceiling_floor,
    is_valid_lot,
    is_valid_tick,
    is_within_band,
    round_to_tick,
    tick_size,
)
from vnstock.schema import Exchange

# ---------- tick_size (HOSE tiered) ----------------------------------------


def test_hose_tick_under_10k() -> None:
    """HOSE < 10,000 VND → 10 VND tick."""
    assert tick_size(5_000, Exchange.HOSE) == 10


def test_hose_tick_10k_to_50k() -> None:
    """HOSE 10,000-49,950 → 50 VND tick."""
    assert tick_size(25_000, Exchange.HOSE) == 50
    assert tick_size(49_950, Exchange.HOSE) == 50


def test_hose_tick_above_50k() -> None:
    """HOSE >= 50,000 → 100 VND tick."""
    assert tick_size(50_000, Exchange.HOSE) == 100
    assert tick_size(100_000, Exchange.HOSE) == 100


def test_hnx_tick_flat_100() -> None:
    assert tick_size(5_000, Exchange.HNX) == 100
    assert tick_size(100_000, Exchange.HNX) == 100


def test_upcom_tick_flat_100() -> None:
    assert tick_size(5_000, Exchange.UPCOM) == 100


def test_tick_size_rejects_zero() -> None:
    with pytest.raises(ValueError, match="price_vnd"):
        tick_size(0, Exchange.HOSE)


# ---------- round_to_tick --------------------------------------------------


def test_round_down() -> None:
    """75,070 → 75,000 (down to nearest 100)."""
    assert round_to_tick(75_070, Exchange.HOSE, mode="down") == 75_000


def test_round_up() -> None:
    assert round_to_tick(75_070, Exchange.HOSE, mode="up") == 75_100


def test_round_nearest_down() -> None:
    assert round_to_tick(75_040, Exchange.HOSE, mode="nearest") == 75_000


def test_round_nearest_up() -> None:
    assert round_to_tick(75_060, Exchange.HOSE, mode="nearest") == 75_100


def test_round_invalid_mode() -> None:
    with pytest.raises(ValueError, match="mode"):
        round_to_tick(75_000, Exchange.HOSE, mode="sideways")


# ---------- is_valid_tick --------------------------------------------------


def test_valid_tick_hose_under_10k() -> None:
    assert is_valid_tick(5_000, Exchange.HOSE) is True
    assert is_valid_tick(5_005, Exchange.HOSE) is False


def test_valid_tick_hose_above_50k() -> None:
    assert is_valid_tick(75_100, Exchange.HOSE) is True
    assert is_valid_tick(75_050, Exchange.HOSE) is False


def test_valid_tick_hnx() -> None:
    """HNX uses a flat 100 VND tick."""
    assert is_valid_tick(7_500, Exchange.HNX) is True
    assert is_valid_tick(7_555, Exchange.HNX) is False


def test_valid_tick_zero_invalid() -> None:
    assert is_valid_tick(0, Exchange.HOSE) is False


# ---------- is_valid_lot ---------------------------------------------------


def test_valid_lot_100() -> None:
    assert is_valid_lot(100, Exchange.HOSE) is True
    assert is_valid_lot(500, Exchange.HOSE) is True
    assert is_valid_lot(1_000_000, Exchange.HOSE) is True


def test_invalid_lot_not_multiple() -> None:
    assert is_valid_lot(150, Exchange.HOSE) is False


def test_invalid_lot_zero_or_negative() -> None:
    assert is_valid_lot(0, Exchange.HOSE) is False
    assert is_valid_lot(-100, Exchange.HOSE) is False


# ---------- ceiling_floor --------------------------------------------------


def test_ceiling_floor_hose_normal() -> None:
    """HOSE @ 50,000 ref → ceiling 53,500, floor 46,500."""
    ceiling, floor = ceiling_floor(50_000, Exchange.HOSE)
    assert ceiling == 53_500
    assert floor == 46_500


def test_ceiling_floor_hnx_normal() -> None:
    """HNX ±10% on 50,000 → 55,000 / 45,000."""
    ceiling, floor = ceiling_floor(50_000, Exchange.HNX)
    assert ceiling == 55_000
    assert floor == 45_000


def test_ceiling_floor_upcom_normal() -> None:
    """UPCoM ±15% on 50,000 → 57,500 / 42,500."""
    ceiling, floor = ceiling_floor(50_000, Exchange.UPCOM)
    assert ceiling == 57_500
    assert floor == 42_500


def test_ceiling_floor_ipo_wider() -> None:
    """HOSE IPO day → ±20% wider band."""
    ceiling, floor = ceiling_floor(50_000, Exchange.HOSE, is_ipo_day=True)
    normal_ceiling, normal_floor = ceiling_floor(50_000, Exchange.HOSE)
    assert ceiling > normal_ceiling
    assert floor < normal_floor


def test_ceiling_floor_rejects_zero_ref() -> None:
    with pytest.raises(ValueError, match="reference"):
        ceiling_floor(0, Exchange.HOSE)


# ---------- is_within_band -------------------------------------------------


def test_within_band_at_reference() -> None:
    """Trading at reference price is always within band."""
    assert is_within_band(50_000, 50_000, Exchange.HOSE) is True


def test_within_band_at_ceiling() -> None:
    """Trading at the ceiling is within band (inclusive)."""
    assert is_within_band(53_500, 50_000, Exchange.HOSE) is True


def test_within_band_above_ceiling() -> None:
    assert is_within_band(54_000, 50_000, Exchange.HOSE) is False


def test_within_band_below_floor() -> None:
    assert is_within_band(46_000, 50_000, Exchange.HOSE) is False


def test_within_band_upcom_wider() -> None:
    """A price that breaches HOSE band may sit inside UPCoM band."""
    # ±10% from 50,000: 55,000. HOSE band is 53,500; UPCoM is 57,500.
    assert is_within_band(55_000, 50_000, Exchange.HOSE) is False
    assert is_within_band(55_000, 50_000, Exchange.UPCOM) is True
