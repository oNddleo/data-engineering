"""Wallet-specific code → canonical (status, amount, timestamp).

Each wallet uses a different encoding for the same concept:

* **VNPay** — ``vnp_ResponseCode`` is a 2-char string. ``"00"`` is the
  only fully-settled state per the VNPay IPN docs; ``"07"`` is
  "suspicious / under bank review" (pending), and everything else is a
  terminal failure (insufficient balance, OTP wrong, customer
  cancelled, etc.). ``vnp_Amount`` is the VND amount *multiplied by
  100* — VNPay encodes everything in the smallest currency unit even
  though VND has no fractional cent. ``vnp_PayDate`` is local-time
  ``yyyyMMddHHmmss`` with no zone info; we tag it with UTC+7.
* **MoMo** — ``resultCode`` is an integer. ``0`` and ``9000`` are
  success (the latter is "authorisation successful, capture
  pending"). ``1000``–``1006`` cover transient/pending states.
  Everything else is failure. Amount is in raw VND. ``responseTime``
  is epoch milliseconds in UTC.
* **ZaloPay** — ``status`` is an integer: ``1`` success, ``3`` pending
  (processing), anything else failure. Amount in raw VND.
  ``server_time`` is epoch milliseconds in UTC.

The two pending ranges (``07`` for VNPay, ``1000``–``1006`` for MoMo,
``3`` for ZaloPay) matter because a same-day reconciliation run will
see them as "not yet settled" — they're expected to reappear in
tomorrow's file as either SUCCESS or FAILED. Classifying them as
FAILED would create a false MERCHANT_ONLY discrepancy.
"""

from __future__ import annotations

from datetime import datetime, timezone

from vmzrecon.schema import VN_TZ, Status

_VNPAY_SUCCESS = frozenset({"00"})
_VNPAY_PENDING = frozenset({"07"})

_MOMO_SUCCESS = frozenset({0, 9000})
_MOMO_PENDING = frozenset({1000, 1001, 1002, 1003, 1004, 1005, 1006, 7000, 7001, 7002})

_ZALOPAY_SUCCESS = frozenset({1})
_ZALOPAY_PENDING = frozenset({3})


def status_from_vnpay(code: str) -> Status:
    """Map a ``vnp_ResponseCode`` string to a canonical :class:`Status`.

    Empty or whitespace input is treated as PENDING — settlement files
    occasionally have blank rows for in-flight transactions.
    """
    code = code.strip()
    if not code:
        return Status.PENDING
    if code in _VNPAY_SUCCESS:
        return Status.SUCCESS
    if code in _VNPAY_PENDING:
        return Status.PENDING
    return Status.FAILED


def status_from_momo(code: int) -> Status:
    """Map a MoMo ``resultCode`` integer to canonical :class:`Status`."""
    if code in _MOMO_SUCCESS:
        return Status.SUCCESS
    if code in _MOMO_PENDING:
        return Status.PENDING
    return Status.FAILED


def status_from_zalopay(code: int) -> Status:
    """Map a ZaloPay ``status`` integer to canonical :class:`Status`."""
    if code in _ZALOPAY_SUCCESS:
        return Status.SUCCESS
    if code in _ZALOPAY_PENDING:
        return Status.PENDING
    return Status.FAILED


def vnpay_amount_to_vnd(raw: int) -> int:
    """Convert ``vnp_Amount`` (VND × 100) to plain integer VND.

    Raises if the value is not divisible by 100 — that would mean a
    half-đồng amount which is impossible in real settlement data and
    almost certainly a parser bug or corrupted row.
    """
    if raw < 0:
        raise ValueError(f"vnp_Amount must be >= 0, got {raw}")
    if raw % 100 != 0:
        raise ValueError(f"vnp_Amount must be a multiple of 100 (VND × 100), got {raw}")
    return raw // 100


def vnpay_paydate_to_datetime(s: str) -> datetime:
    """Parse a ``vnp_PayDate`` (``yyyyMMddHHmmss`` local time) into UTC+7."""
    s = s.strip()
    if len(s) != 14 or not s.isdigit():
        raise ValueError(f"vnp_PayDate must be 14-digit yyyyMMddHHmmss, got {s!r}")
    return datetime(
        year=int(s[0:4]),
        month=int(s[4:6]),
        day=int(s[6:8]),
        hour=int(s[8:10]),
        minute=int(s[10:12]),
        second=int(s[12:14]),
        tzinfo=VN_TZ,
    )


def epoch_ms_to_datetime(ms: int) -> datetime:
    """Convert epoch milliseconds (UTC) to a timezone-aware datetime in UTC+7."""
    if ms < 0:
        raise ValueError(f"epoch ms must be >= 0, got {ms}")
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).astimezone(VN_TZ)


__all__ = [
    "epoch_ms_to_datetime",
    "status_from_momo",
    "status_from_vnpay",
    "status_from_zalopay",
    "vnpay_amount_to_vnd",
    "vnpay_paydate_to_datetime",
]
