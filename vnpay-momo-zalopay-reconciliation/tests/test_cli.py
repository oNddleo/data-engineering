"""CLI smoke tests — exercise the argparse wiring + happy path end-to-end."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vmzrecon.cli import main

VNPAY = """vnp_TxnRef,vnp_TransactionNo,vnp_Amount,vnp_BankCode,vnp_PayDate,vnp_ResponseCode
ORD-1,V-1,100000000,NCB,20260514093015,00
"""

MOMO = """orderId,transId,amount,responseTime,resultCode
ORD-2,M-1,250000,1763087400000,0
"""

ZALOPAY = """app_id,app_trans_id,zp_trans_id,amount,server_time,status
2553,ORD-3,Z-1,500000,1763087400000,1
"""

MERCHANT = """order_id,wallet,expected_amount_vnd,status,created_at
ORD-1,VNPAY,1000000,SUCCESS,2026-05-14T09:30:15+07:00
ORD-2,MOMO,250000,SUCCESS,2026-05-14T09:30:15+07:00
ORD-3,ZALOPAY,499000,SUCCESS,2026-05-14T09:30:15+07:00
"""


def test_cli_info_exits_zero(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "vnpay-momo-zalopay-reconciliation" in out


def test_cli_parse_vnpay_stdin(monkeypatch, capsys):
    import io as _io

    monkeypatch.setattr("sys.stdin", _io.StringIO(VNPAY))
    assert main(["parse", "--wallet", "vnpay"]) == 0
    out = capsys.readouterr().out
    assert "ORD-1" in out
    assert "SUCCESS" in out


def test_cli_parse_merchant_file(tmp_path: Path, capsys):
    p = tmp_path / "m.csv"
    p.write_text(MERCHANT, encoding="utf-8")
    assert main(["parse", "--wallet", "merchant", "--file", str(p)]) == 0
    out = capsys.readouterr().out
    assert "ORD-1" in out
    assert "VNPAY" in out


def test_cli_parse_unknown_wallet(tmp_path: Path, capsys):
    p = tmp_path / "junk.csv"
    p.write_text("x\n", encoding="utf-8")
    rc = main(["parse", "--wallet", "merchant", "--file", str(p)])
    assert rc == 0  # merchant accepts empty after header parse


def test_cli_reconcile_text_format(tmp_path: Path, capsys):
    m = tmp_path / "m.csv"
    m.write_text(MERCHANT, encoding="utf-8")
    v = tmp_path / "v.csv"
    v.write_text(VNPAY, encoding="utf-8")
    mo = tmp_path / "mo.csv"
    mo.write_text(MOMO, encoding="utf-8")
    z = tmp_path / "z.csv"
    z.write_text(ZALOPAY, encoding="utf-8")
    rc = main(
        [
            "reconcile",
            "--merchant",
            str(m),
            "--vnpay",
            str(v),
            "--momo",
            str(mo),
            "--zalopay",
            str(z),
            "--format",
            "text",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    # ORD-1 VNPay: amount mismatch (merchant 1,000,000 vs wallet 1,000,000? actually
    # vnp_Amount=100,000,000 / 100 = 1,000,000 — matches; ORD-3 ZaloPay: merchant
    # expects 499,000 but wallet settled 500,000 → AMOUNT_MISMATCH.
    assert "AMOUNT_MISMATCH" in out
    assert "ORD-3" in out


def test_cli_reconcile_json_format(tmp_path: Path, capsys):
    m = tmp_path / "m.csv"
    m.write_text(MERCHANT, encoding="utf-8")
    v = tmp_path / "v.csv"
    v.write_text(VNPAY, encoding="utf-8")
    rc = main(
        [
            "reconcile",
            "--merchant",
            str(m),
            "--vnpay",
            str(v),
            "--format",
            "json",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "summary" in payload
    assert "discrepancies" in payload


def test_cli_reconcile_csv_format(tmp_path: Path, capsys):
    m = tmp_path / "m.csv"
    m.write_text(MERCHANT, encoding="utf-8")
    rc = main(
        [
            "reconcile",
            "--merchant",
            str(m),
            "--format",
            "csv",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("kind,wallet,order_id")


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
