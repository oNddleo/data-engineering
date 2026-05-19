"""Rating engine: tariff application + VAT + block-6 rounding."""

from __future__ import annotations

from datetime import datetime

import pytest

from cdrpipe.rating import (
    DEFAULT_TARIFF,
    VAT_BPS,
    TariffTable,
    billable_minutes,
    is_peak,
    rate,
)
from cdrpipe.schema import VN_TZ, Carrier, CDRKind

from ._fixtures import data_cdr, make_cdr, sms_cdr, voice_cdr

# ---------- is_peak / billable_minutes --------------------------------------


@pytest.mark.parametrize("hour", [6, 7, 12, 18, 21])
def test_is_peak_business_hours(hour: int) -> None:
    assert is_peak(hour) is True


@pytest.mark.parametrize("hour", [0, 3, 5, 22, 23])
def test_is_peak_night_hours(hour: int) -> None:
    assert is_peak(hour) is False


@pytest.mark.parametrize(
    ("seconds", "minutes"),
    [
        (0, 0),
        (5, 0),  # under block → free
        (6, 1),
        (59, 1),
        (60, 1),
        (61, 2),
        (120, 2),
        (121, 3),
    ],
)
def test_billable_minutes(seconds: int, minutes: int) -> None:
    assert billable_minutes(seconds) == minutes


# ---------- rate(): voice ---------------------------------------------------


def test_rate_voice_on_net_peak() -> None:
    # Viettel → Viettel, daytime
    at = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)
    c = voice_cdr(subscriber="0961234567", peer="0971234567", duration_seconds=60, at=at)
    r = rate(c)
    assert r.subscriber_carrier is Carrier.VIETTEL
    assert r.peer_carrier is Carrier.VIETTEL
    assert r.is_peak is True
    assert r.rated_amount_vnd == 1_580  # 1 min on-net peak


def test_rate_voice_off_net_peak() -> None:
    # Viettel → VinaPhone, daytime
    at = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)
    c = voice_cdr(subscriber="0961234567", peer="0911234567", duration_seconds=60, at=at)
    r = rate(c)
    assert r.subscriber_carrier is Carrier.VIETTEL
    assert r.peer_carrier is Carrier.VINAPHONE
    assert r.rated_amount_vnd == 1_780


def test_rate_voice_on_net_off_peak() -> None:
    at = datetime(2026, 5, 18, 2, 0, 0, tzinfo=VN_TZ)
    c = voice_cdr(subscriber="0961234567", peer="0971234567", duration_seconds=60, at=at)
    r = rate(c)
    assert r.is_peak is False
    assert r.rated_amount_vnd == 1_280


def test_rate_voice_off_net_off_peak() -> None:
    at = datetime(2026, 5, 18, 23, 0, 0, tzinfo=VN_TZ)
    c = voice_cdr(subscriber="0961234567", peer="0911234567", duration_seconds=60, at=at)
    r = rate(c)
    assert r.is_peak is False
    assert r.rated_amount_vnd == 1_480


def test_rate_voice_premium_overrides_carrier() -> None:
    """A 1900 call is billed at premium rate regardless of network."""
    at = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)
    c = make_cdr(
        kind=CDRKind.VOICE,
        peer_msisdn="19001234",
        duration_seconds=60,
        is_premium=True,
        occurred_at=at,
    )
    r = rate(c)
    assert r.rated_amount_vnd == 8_000


def test_rate_voice_roaming_overrides_tariff() -> None:
    """Roaming voice is billed flat at 8,000 VND/min."""
    at = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)
    c = voice_cdr(duration_seconds=60, at=at, is_roaming=True)
    r = rate(c)
    assert r.rated_amount_vnd == 8_000


def test_rate_voice_under_block_is_free() -> None:
    """Calls under 6 seconds are not billable."""
    c = voice_cdr(duration_seconds=3)
    r = rate(c)
    assert r.rated_amount_vnd == 0
    assert r.vat_amount_vnd == 0


def test_rate_voice_block_rounding_two_minutes() -> None:
    """A 61-second call rounds up to 2 minutes."""
    at = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)
    c = voice_cdr(subscriber="0961234567", peer="0971234567", duration_seconds=61, at=at)
    r = rate(c)
    assert r.rated_amount_vnd == 2 * 1_580


# ---------- rate(): SMS -----------------------------------------------------


def test_rate_sms_on_net() -> None:
    c = sms_cdr(subscriber="0961234567", peer="0971234567")
    r = rate(c)
    assert r.rated_amount_vnd == 290


def test_rate_sms_off_net() -> None:
    c = sms_cdr(subscriber="0961234567", peer="0911234567")
    r = rate(c)
    assert r.rated_amount_vnd == 390


def test_rate_sms_roaming() -> None:
    c = sms_cdr(is_roaming=True)
    r = rate(c)
    assert r.rated_amount_vnd == 2_500


# ---------- rate(): DATA ----------------------------------------------------


def test_rate_data_one_mb() -> None:
    c = data_cdr(bytes_used=1024 * 1024)
    r = rate(c)
    assert r.rated_amount_vnd == 50


def test_rate_data_round_up_partial_mb() -> None:
    """Partial MB rounds up to next whole MB."""
    c = data_cdr(bytes_used=1024 * 1024 + 1)
    r = rate(c)
    assert r.rated_amount_vnd == 100  # 2 MB × 50


def test_rate_data_roaming() -> None:
    c = data_cdr(bytes_used=1024 * 1024, is_roaming=True)
    r = rate(c)
    assert r.rated_amount_vnd == 200


# ---------- VAT -------------------------------------------------------------


def test_rate_vat_is_ten_percent() -> None:
    """VAT must be exactly 10% of the rated amount."""
    at = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)
    c = voice_cdr(subscriber="0961234567", peer="0971234567", duration_seconds=60, at=at)
    r = rate(c)
    assert r.vat_amount_vnd == r.rated_amount_vnd // 10


def test_rate_vat_bps_constant() -> None:
    """The published VAT rate (10%) is encoded as basis points."""
    assert VAT_BPS == 1_000


# ---------- custom tariff ---------------------------------------------------


def test_rate_custom_tariff() -> None:
    """A caller-supplied TariffTable overrides DEFAULT_TARIFF."""
    custom = TariffTable(voice_on_net_peak_per_min=2_000)
    at = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)
    c = voice_cdr(subscriber="0961234567", peer="0971234567", duration_seconds=60, at=at)
    r = rate(c, tariff=custom)
    assert r.rated_amount_vnd == 2_000


def test_default_tariff_immutable() -> None:
    """DEFAULT_TARIFF is a frozen dataclass."""
    with pytest.raises((AttributeError, TypeError)):
        DEFAULT_TARIFF.voice_on_net_peak_per_min = 999  # type: ignore[misc]


def test_rate_data_peer_unknown() -> None:
    """DATA CDRs have no peer; peer_carrier is UNKNOWN."""
    c = data_cdr(bytes_used=5 * 1024 * 1024)
    r = rate(c)
    assert r.peer_carrier is Carrier.UNKNOWN
