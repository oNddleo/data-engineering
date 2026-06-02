"""CSV parsers for VNPay / MoMo / ZaloPay settlement files + merchant ledger.

Each settlement file's column layout is dictated by the wallet vendor
and not interchangeable. The parsers normalise into :class:`WalletTxn`
(wallet side) and :class:`MerchantOrder` (merchant side).

All parsers are forgiving on:

* Header column ordering — DictReader handles that.
* Whitespace around values.
* Empty trailing rows.

But strict on:

* Missing required columns → :class:`ParseError`.
* Malformed amounts, codes, or timestamps → :class:`ParseError` with
  the offending row number (1-indexed, header counted as row 1) so a
  data engineer can grep the original file.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import TYPE_CHECKING

from vmzrecon.normalize import (
    epoch_ms_to_datetime,
    status_from_momo,
    status_from_vnpay,
    status_from_zalopay,
    vnpay_amount_to_vnd,
    vnpay_paydate_to_datetime,
)
from vmzrecon.schema import MerchantOrder, Status, Wallet, WalletTxn

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


class ParseError(Exception):
    """Raised when a settlement-file row is malformed.

    ``row_number`` is 1-indexed and counts the header as row 1, so the
    first data row is row 2 — matching what a user sees in a
    spreadsheet.
    """

    def __init__(self, file_kind: str, row_number: int, field: str, message: str) -> None:
        super().__init__(f"{file_kind} row {row_number}: {field}: {message}")
        self.file_kind = file_kind
        self.row_number = row_number
        self.field = field
        self.message = message


_VNPAY_REQUIRED = (
    "vnp_TxnRef",
    "vnp_TransactionNo",
    "vnp_Amount",
    "vnp_PayDate",
    "vnp_ResponseCode",
)
_MOMO_REQUIRED = ("orderId", "transId", "amount", "responseTime", "resultCode")
_ZALOPAY_REQUIRED = ("app_trans_id", "zp_trans_id", "amount", "server_time", "status")
_MERCHANT_REQUIRED = ("order_id", "wallet", "expected_amount_vnd", "status", "created_at")


def _check_columns(file_kind: str, header: Iterable[str], required: Iterable[str]) -> None:
    cols = set(header)
    missing = [c for c in required if c not in cols]
    if missing:
        raise ParseError(
            file_kind=file_kind,
            row_number=1,
            field=",".join(missing),
            message=f"missing required columns: {missing}",
        )


def _open_csv(source: str | io.StringIO) -> Iterator[dict[str, str]]:
    if isinstance(source, str):
        reader = csv.DictReader(io.StringIO(source))
    else:
        reader = csv.DictReader(source)
    yield from reader


def _int_field(file_kind: str, row_no: int, field: str, raw: str) -> int:
    try:
        return int(raw.strip())
    except ValueError as e:
        raise ParseError(
            file_kind=file_kind, row_number=row_no, field=field, message=f"not an integer ({raw!r})"
        ) from e


def parse_vnpay_csv(text: str) -> list[WalletTxn]:
    """Parse a VNPay settlement CSV.

    Required columns: ``vnp_TxnRef`` (merchant order id),
    ``vnp_TransactionNo`` (VNPay txn id), ``vnp_Amount`` (VND × 100),
    ``vnp_PayDate`` (``yyyyMMddHHmmss`` local), ``vnp_ResponseCode``.
    Optional ``vnp_BankCode``.
    """
    rows = list(_open_csv(text))
    if not rows:
        return []
    _check_columns("vnpay", rows[0].keys(), _VNPAY_REQUIRED)
    out: list[WalletTxn] = []
    for i, row in enumerate(rows, start=2):
        raw_amount = _int_field("vnpay", i, "vnp_Amount", row["vnp_Amount"])
        try:
            amount = vnpay_amount_to_vnd(raw_amount)
        except ValueError as e:
            raise ParseError("vnpay", i, "vnp_Amount", str(e)) from e
        try:
            paid_at = vnpay_paydate_to_datetime(row["vnp_PayDate"])
        except ValueError as e:
            raise ParseError("vnpay", i, "vnp_PayDate", str(e)) from e
        code = row["vnp_ResponseCode"].strip()
        out.append(
            WalletTxn(
                wallet=Wallet.VNPAY,
                merchant_order_id=row["vnp_TxnRef"].strip(),
                wallet_txn_id=row["vnp_TransactionNo"].strip(),
                amount_vnd=amount,
                status=status_from_vnpay(code),
                paid_at=paid_at,
                bank_code=(row.get("vnp_BankCode") or "").strip() or None,
                raw_response_code=code,
            )
        )
    return out


def parse_momo_csv(text: str) -> list[WalletTxn]:
    """Parse a MoMo settlement CSV.

    Required columns: ``orderId`` (merchant), ``transId`` (MoMo),
    ``amount`` (raw VND), ``responseTime`` (epoch ms), ``resultCode``.
    """
    rows = list(_open_csv(text))
    if not rows:
        return []
    _check_columns("momo", rows[0].keys(), _MOMO_REQUIRED)
    out: list[WalletTxn] = []
    for i, row in enumerate(rows, start=2):
        amount = _int_field("momo", i, "amount", row["amount"])
        if amount < 0:
            raise ParseError("momo", i, "amount", f"amount must be >= 0, got {amount}")
        ms = _int_field("momo", i, "responseTime", row["responseTime"])
        try:
            paid_at = epoch_ms_to_datetime(ms)
        except ValueError as e:
            raise ParseError("momo", i, "responseTime", str(e)) from e
        code = _int_field("momo", i, "resultCode", row["resultCode"])
        out.append(
            WalletTxn(
                wallet=Wallet.MOMO,
                merchant_order_id=row["orderId"].strip(),
                wallet_txn_id=row["transId"].strip(),
                amount_vnd=amount,
                status=status_from_momo(code),
                paid_at=paid_at,
                bank_code=None,
                raw_response_code=str(code),
            )
        )
    return out


def parse_zalopay_csv(text: str) -> list[WalletTxn]:
    """Parse a ZaloPay settlement CSV.

    Required columns: ``app_trans_id`` (merchant order id, often
    prefixed ``yymmdd_``), ``zp_trans_id`` (ZaloPay txn id),
    ``amount`` (raw VND), ``server_time`` (epoch ms), ``status``.
    """
    rows = list(_open_csv(text))
    if not rows:
        return []
    _check_columns("zalopay", rows[0].keys(), _ZALOPAY_REQUIRED)
    out: list[WalletTxn] = []
    for i, row in enumerate(rows, start=2):
        amount = _int_field("zalopay", i, "amount", row["amount"])
        if amount < 0:
            raise ParseError("zalopay", i, "amount", f"amount must be >= 0, got {amount}")
        ms = _int_field("zalopay", i, "server_time", row["server_time"])
        try:
            paid_at = epoch_ms_to_datetime(ms)
        except ValueError as e:
            raise ParseError("zalopay", i, "server_time", str(e)) from e
        code = _int_field("zalopay", i, "status", row["status"])
        out.append(
            WalletTxn(
                wallet=Wallet.ZALOPAY,
                merchant_order_id=row["app_trans_id"].strip(),
                wallet_txn_id=row["zp_trans_id"].strip(),
                amount_vnd=amount,
                status=status_from_zalopay(code),
                paid_at=paid_at,
                bank_code=None,
                raw_response_code=str(code),
            )
        )
    return out


def parse_merchant_csv(text: str) -> list[MerchantOrder]:
    """Parse the merchant order ledger CSV.

    Required columns: ``order_id``, ``wallet`` (one of ``VNPAY``,
    ``MOMO``, ``ZALOPAY``), ``expected_amount_vnd`` (raw VND),
    ``status`` (``SUCCESS``/``FAILED``/``PENDING`` — merchant's
    view), ``created_at`` (ISO-8601 with offset).
    """
    rows = list(_open_csv(text))
    if not rows:
        return []
    _check_columns("merchant", rows[0].keys(), _MERCHANT_REQUIRED)
    out: list[MerchantOrder] = []
    for i, row in enumerate(rows, start=2):
        wallet_s = row["wallet"].strip().upper()
        try:
            wallet = Wallet(wallet_s)
        except ValueError as e:
            raise ParseError("merchant", i, "wallet", f"unknown wallet {wallet_s!r}") from e
        amount = _int_field("merchant", i, "expected_amount_vnd", row["expected_amount_vnd"])
        if amount < 0:
            raise ParseError("merchant", i, "expected_amount_vnd", f"must be >= 0, got {amount}")
        status_s = row["status"].strip().upper()
        try:
            status = Status(status_s)
        except ValueError as e:
            raise ParseError("merchant", i, "status", f"unknown status {status_s!r}") from e
        try:
            created_at = datetime.fromisoformat(row["created_at"].strip())
        except ValueError as e:
            raise ParseError("merchant", i, "created_at", f"not ISO-8601: {e}") from e
        if created_at.tzinfo is None:
            raise ParseError("merchant", i, "created_at", "must include a timezone offset")
        out.append(
            MerchantOrder(
                order_id=row["order_id"].strip(),
                wallet=wallet,
                expected_amount_vnd=amount,
                status=status,
                created_at=created_at,
            )
        )
    return out


__all__ = [
    "ParseError",
    "parse_merchant_csv",
    "parse_momo_csv",
    "parse_vnpay_csv",
    "parse_zalopay_csv",
]
