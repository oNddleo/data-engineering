"""CSV parser tests."""

from __future__ import annotations

import pytest

from vmzrecon.parsers import (
    ParseError,
    parse_merchant_csv,
    parse_momo_csv,
    parse_vnpay_csv,
    parse_zalopay_csv,
)
from vmzrecon.schema import Status, Wallet

VNPAY_GOOD = """vnp_TxnRef,vnp_TransactionNo,vnp_Amount,vnp_BankCode,vnp_PayDate,vnp_ResponseCode
ORD-1001,14528391,100000000,NCB,20260514093015,00
ORD-1002,14528392,250000000,VCB,20260514093122,24
"""

MOMO_GOOD = """orderId,transId,amount,responseTime,resultCode
ORD-1001,2614528391,1000000,1763087400000,0
ORD-1003,2614528393,500000,1763087500000,1001
"""

ZALOPAY_GOOD = """app_id,app_trans_id,zp_trans_id,amount,server_time,status
2553,260514_ORD-1001,260514000111,1000000,1763087400000,1
2553,260514_ORD-1004,260514000222,750000,1763087600000,2
"""

MERCHANT_GOOD = """order_id,wallet,expected_amount_vnd,status,created_at
ORD-1001,VNPAY,1000000,SUCCESS,2026-05-14T09:30:15+07:00
ORD-1002,VNPAY,2500000,FAILED,2026-05-14T09:31:22+07:00
"""


def test_parse_vnpay_basic():
    txns = parse_vnpay_csv(VNPAY_GOOD)
    assert len(txns) == 2
    a, b = txns
    assert a.wallet is Wallet.VNPAY
    assert a.merchant_order_id == "ORD-1001"
    assert a.wallet_txn_id == "14528391"
    assert a.amount_vnd == 1_000_000
    assert a.status is Status.SUCCESS
    assert a.bank_code == "NCB"
    assert b.status is Status.FAILED  # vnp_ResponseCode=24


def test_parse_vnpay_empty_returns_empty():
    assert parse_vnpay_csv("") == []


def test_parse_vnpay_missing_column_raises():
    bad = "vnp_TxnRef,vnp_TransactionNo,vnp_Amount,vnp_PayDate\nORD,1,100,2026\n"
    with pytest.raises(ParseError) as e:
        parse_vnpay_csv(bad)
    assert "vnp_ResponseCode" in str(e.value)


def test_parse_vnpay_bad_amount_row_number():
    bad = VNPAY_GOOD.replace("100000000", "abc")
    with pytest.raises(ParseError) as e:
        parse_vnpay_csv(bad)
    assert e.value.row_number == 2
    assert e.value.field == "vnp_Amount"


def test_parse_vnpay_amount_not_div_by_100():
    bad = VNPAY_GOOD.replace("100000000", "100000001")
    with pytest.raises(ParseError) as e:
        parse_vnpay_csv(bad)
    assert e.value.field == "vnp_Amount"


def test_parse_vnpay_bad_paydate():
    bad = VNPAY_GOOD.replace("20260514093015", "ABCDEFGHIJKLMN")
    with pytest.raises(ParseError) as e:
        parse_vnpay_csv(bad)
    assert e.value.field == "vnp_PayDate"


def test_parse_momo_basic():
    txns = parse_momo_csv(MOMO_GOOD)
    assert len(txns) == 2
    a, b = txns
    assert a.wallet is Wallet.MOMO
    assert a.amount_vnd == 1_000_000
    assert a.status is Status.SUCCESS
    assert b.status is Status.PENDING  # 1001 is in pending range


def test_parse_momo_negative_amount():
    bad = MOMO_GOOD.replace("1000000", "-1")
    with pytest.raises(ParseError) as e:
        parse_momo_csv(bad)
    assert e.value.field == "amount"


def test_parse_momo_missing_column():
    bad = "orderId,transId,amount,responseTime\nORD,1,100,1\n"
    with pytest.raises(ParseError):
        parse_momo_csv(bad)


def test_parse_zalopay_basic():
    txns = parse_zalopay_csv(ZALOPAY_GOOD)
    assert len(txns) == 2
    a, b = txns
    assert a.wallet is Wallet.ZALOPAY
    assert a.merchant_order_id == "260514_ORD-1001"
    assert a.amount_vnd == 1_000_000
    assert a.status is Status.SUCCESS
    assert b.status is Status.FAILED


def test_parse_zalopay_missing_column():
    bad = "app_id,app_trans_id,zp_trans_id,amount\n2553,1,2,3\n"
    with pytest.raises(ParseError):
        parse_zalopay_csv(bad)


def test_parse_merchant_basic():
    orders = parse_merchant_csv(MERCHANT_GOOD)
    assert len(orders) == 2
    a, b = orders
    assert a.wallet is Wallet.VNPAY
    assert a.status is Status.SUCCESS
    assert b.status is Status.FAILED


def test_parse_merchant_unknown_wallet():
    bad = "order_id,wallet,expected_amount_vnd,status,created_at\nORD,VIETTELPAY,1,SUCCESS,2026-05-14T09:30:00+07:00\n"
    with pytest.raises(ParseError) as e:
        parse_merchant_csv(bad)
    assert e.value.field == "wallet"


def test_parse_merchant_naive_datetime_rejected():
    bad = "order_id,wallet,expected_amount_vnd,status,created_at\nORD,VNPAY,1,SUCCESS,2026-05-14T09:30:00\n"
    with pytest.raises(ParseError) as e:
        parse_merchant_csv(bad)
    assert e.value.field == "created_at"


def test_parse_merchant_bad_status():
    bad = "order_id,wallet,expected_amount_vnd,status,created_at\nORD,VNPAY,1,REFUNDED,2026-05-14T09:30:00+07:00\n"
    with pytest.raises(ParseError) as e:
        parse_merchant_csv(bad)
    assert e.value.field == "status"


def test_parse_merchant_lowercase_wallet_accepted():
    text = "order_id,wallet,expected_amount_vnd,status,created_at\nORD,vnpay,1,success,2026-05-14T09:30:00+07:00\n"
    orders = parse_merchant_csv(text)
    assert orders[0].wallet is Wallet.VNPAY
    assert orders[0].status is Status.SUCCESS
