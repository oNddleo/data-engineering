"""Wallet-code → canonical normaliser tests."""

from __future__ import annotations

import pytest

from vmzrecon.normalize import (
    epoch_ms_to_datetime,
    status_from_momo,
    status_from_vnpay,
    status_from_zalopay,
    vnpay_amount_to_vnd,
    vnpay_paydate_to_datetime,
)
from vmzrecon.schema import VN_TZ, Status


def test_vnpay_00_is_success():
    assert status_from_vnpay("00") is Status.SUCCESS


def test_vnpay_07_is_pending():
    assert status_from_vnpay("07") is Status.PENDING


def test_vnpay_24_is_failed():  # customer cancelled
    assert status_from_vnpay("24") is Status.FAILED


def test_vnpay_blank_is_pending():
    assert status_from_vnpay("") is Status.PENDING
    assert status_from_vnpay("   ") is Status.PENDING


def test_momo_zero_is_success():
    assert status_from_momo(0) is Status.SUCCESS


def test_momo_9000_is_success():  # captured later, MoMo treats as success
    assert status_from_momo(9000) is Status.SUCCESS


def test_momo_pending_range():
    for code in (1000, 1001, 1006, 7000, 7002):
        assert status_from_momo(code) is Status.PENDING, code


def test_momo_unknown_is_failed():
    assert status_from_momo(99) is Status.FAILED


def test_zalopay_status_codes():
    assert status_from_zalopay(1) is Status.SUCCESS
    assert status_from_zalopay(3) is Status.PENDING
    assert status_from_zalopay(2) is Status.FAILED
    assert status_from_zalopay(-49) is Status.FAILED


def test_vnpay_amount_dividing_by_100():
    assert vnpay_amount_to_vnd(100_000_000) == 1_000_000


def test_vnpay_amount_rejects_not_divisible_by_100():
    with pytest.raises(ValueError):
        vnpay_amount_to_vnd(123)


def test_vnpay_amount_rejects_negative():
    with pytest.raises(ValueError):
        vnpay_amount_to_vnd(-100)


def test_vnpay_paydate_parses_local_to_vn_tz():
    dt = vnpay_paydate_to_datetime("20260514093015")
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second) == (
        2026,
        5,
        14,
        9,
        30,
        15,
    )
    assert dt.tzinfo is not None
    assert dt.utcoffset() == VN_TZ.utcoffset(None)


def test_vnpay_paydate_rejects_short_string():
    with pytest.raises(ValueError):
        vnpay_paydate_to_datetime("2026051409")


def test_vnpay_paydate_rejects_non_digit():
    with pytest.raises(ValueError):
        vnpay_paydate_to_datetime("20260514T9301X")


def test_epoch_ms_converts_to_vn_tz():
    # 2026-05-14T02:30:00Z = 09:30:00 +07
    ms = 1763087400000
    dt = epoch_ms_to_datetime(ms)
    assert dt.utcoffset() == VN_TZ.utcoffset(None)


def test_epoch_ms_rejects_negative():
    with pytest.raises(ValueError):
        epoch_ms_to_datetime(-1)
