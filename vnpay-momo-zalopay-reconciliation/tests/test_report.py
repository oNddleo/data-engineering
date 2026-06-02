"""Report-formatter + summariser tests."""

from __future__ import annotations

import io
import json

from vmzrecon.discrepancy import Discrepancy, DiscrepancyKind
from vmzrecon.report import (
    format_csv_report,
    format_json_report,
    format_text_report,
    summarise,
)
from vmzrecon.schema import Wallet


def _sample() -> list[Discrepancy]:
    return [
        Discrepancy(
            kind=DiscrepancyKind.WALLET_ONLY,
            wallet=Wallet.VNPAY,
            order_id="ORD-1",
            detail="VNPAY settled 100,000 VND but no matching merchant order",
            wallet_amount=100_000,
        ),
        Discrepancy(
            kind=DiscrepancyKind.MERCHANT_ONLY,
            wallet=Wallet.MOMO,
            order_id="ORD-2",
            detail="merchant marked SUCCESS for 250,000 VND via MOMO but settlement file does not contain it",
            merchant_amount=250_000,
        ),
        Discrepancy(
            kind=DiscrepancyKind.AMOUNT_MISMATCH,
            wallet=Wallet.ZALOPAY,
            order_id="ORD-3",
            detail="merchant expected 500,000 VND, wallet settled 499,000 VND",
            wallet_amount=499_000,
            merchant_amount=500_000,
        ),
    ]


def test_summarise_counts_total():
    s = summarise(_sample())
    assert s.total == 3


def test_summarise_net_vnd_missing():
    # merchant_only (+250,000) minus wallet_only (-100,000) = 150,000
    s = summarise(_sample())
    assert s.net_vnd_missing == 150_000


def test_summarise_by_kind():
    s = summarise(_sample())
    assert s.by_kind[DiscrepancyKind.WALLET_ONLY] == 1
    assert s.by_kind[DiscrepancyKind.MERCHANT_ONLY] == 1
    assert s.by_kind[DiscrepancyKind.AMOUNT_MISMATCH] == 1
    assert s.by_kind[DiscrepancyKind.STATUS_MISMATCH] == 0
    assert s.by_kind[DiscrepancyKind.DUPLICATE_IN_WALLET] == 0


def test_summarise_by_wallet():
    s = summarise(_sample())
    assert s.by_wallet[Wallet.VNPAY] == 1
    assert s.by_wallet[Wallet.MOMO] == 1
    assert s.by_wallet[Wallet.ZALOPAY] == 1


def test_summarise_empty():
    s = summarise([])
    assert s.total == 0
    assert s.net_vnd_missing == 0
    assert all(v == 0 for v in s.by_kind.values())


def test_text_report_contains_all_three_orders():
    text = format_text_report(_sample())
    assert "ORD-1" in text
    assert "ORD-2" in text
    assert "ORD-3" in text
    assert "total discrepancies: 3" in text


def test_text_report_empty():
    text = format_text_report([])
    assert "total discrepancies: 0" in text
    assert "details:" not in text  # no detail block when nothing to show


def test_csv_report_has_header_and_rows():
    csv_text = format_csv_report(_sample())
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("kind,wallet,order_id")
    assert len(lines) == 4  # 1 header + 3 rows


def test_csv_report_round_trips_through_csv_reader():
    import csv

    csv_text = format_csv_report(_sample())
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0]["kind"] == "WALLET_ONLY"
    assert rows[0]["wallet_amount_vnd"] == "100000"
    assert rows[0]["merchant_amount_vnd"] == ""


def test_json_report_parses_and_has_summary():
    payload = json.loads(format_json_report(_sample()))
    assert payload["summary"]["total"] == 3
    assert payload["summary"]["net_vnd_missing"] == 150_000
    assert len(payload["discrepancies"]) == 3
    assert payload["discrepancies"][0]["kind"] == "WALLET_ONLY"


def test_json_report_empty():
    payload = json.loads(format_json_report([]))
    assert payload["summary"]["total"] == 0
    assert payload["discrepancies"] == []
