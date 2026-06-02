"""``vmzrecon`` command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vmzrecon.schema import WalletTxn


def _read(path: str | None) -> str:
    if path is None:
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def cmd_info(_args: argparse.Namespace) -> int:
    from vmzrecon import __version__

    print(f"vnpay-momo-zalopay-reconciliation {__version__}")
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    from vmzrecon.parsers import (
        parse_merchant_csv,
        parse_momo_csv,
        parse_vnpay_csv,
        parse_zalopay_csv,
    )

    text = _read(args.file)
    wallet = args.wallet.lower()
    if wallet == "vnpay":
        txns = parse_vnpay_csv(text)
        for t in txns:
            print(
                f"VNPAY {t.merchant_order_id} {t.wallet_txn_id} "
                f"{t.amount_vnd:,} VND {t.status.value} {t.paid_at.isoformat()}"
            )
    elif wallet == "momo":
        for t in parse_momo_csv(text):
            print(
                f"MOMO  {t.merchant_order_id} {t.wallet_txn_id} "
                f"{t.amount_vnd:,} VND {t.status.value} {t.paid_at.isoformat()}"
            )
    elif wallet == "zalopay":
        for t in parse_zalopay_csv(text):
            print(
                f"ZALO  {t.merchant_order_id} {t.wallet_txn_id} "
                f"{t.amount_vnd:,} VND {t.status.value} {t.paid_at.isoformat()}"
            )
    elif wallet == "merchant":
        for o in parse_merchant_csv(text):
            print(
                f"MERCH {o.order_id} {o.wallet.value} "
                f"{o.expected_amount_vnd:,} VND {o.status.value} {o.created_at.isoformat()}"
            )
    else:
        print(f"unknown --wallet {args.wallet!r}", file=sys.stderr)
        return 2
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    from vmzrecon.matcher import reconcile
    from vmzrecon.parsers import (
        parse_merchant_csv,
        parse_momo_csv,
        parse_vnpay_csv,
        parse_zalopay_csv,
    )
    from vmzrecon.report import format_csv_report, format_json_report, format_text_report

    merchant_orders = parse_merchant_csv(Path(args.merchant).read_text(encoding="utf-8"))
    wallet_txns: list[WalletTxn] = []
    if args.vnpay:
        wallet_txns.extend(parse_vnpay_csv(Path(args.vnpay).read_text(encoding="utf-8")))
    if args.momo:
        wallet_txns.extend(parse_momo_csv(Path(args.momo).read_text(encoding="utf-8")))
    if args.zalopay:
        wallet_txns.extend(parse_zalopay_csv(Path(args.zalopay).read_text(encoding="utf-8")))

    discrepancies = reconcile(merchant_orders, wallet_txns)
    if args.format == "csv":
        sys.stdout.write(format_csv_report(discrepancies))
    elif args.format == "json":
        sys.stdout.write(format_json_report(discrepancies))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_text_report(discrepancies))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vmzrecon",
        description="Reconcile VNPay / MoMo / ZaloPay daily settlement files against a merchant order ledger.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    parse_p = sub.add_parser(
        "parse", help="parse one settlement / merchant CSV and dump normalised rows"
    )
    parse_p.add_argument(
        "--wallet", required=True, choices=["vnpay", "momo", "zalopay", "merchant"]
    )
    parse_p.add_argument("--file", default=None, help="path to CSV; stdin if omitted")
    parse_p.set_defaults(func=cmd_parse)

    rec = sub.add_parser("reconcile", help="run 3-way recon and print a report")
    rec.add_argument("--merchant", required=True, help="path to merchant orders CSV")
    rec.add_argument("--vnpay", default=None, help="path to VNPay settlement CSV")
    rec.add_argument("--momo", default=None, help="path to MoMo settlement CSV")
    rec.add_argument("--zalopay", default=None, help="path to ZaloPay settlement CSV")
    rec.add_argument("--format", choices=["text", "csv", "json"], default="text")
    rec.set_defaults(func=cmd_reconcile)

    args = p.parse_args(argv)
    result = args.func(args)
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
