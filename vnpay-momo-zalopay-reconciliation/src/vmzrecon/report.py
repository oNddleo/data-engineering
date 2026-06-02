"""Text / CSV / JSON formatters for a reconciliation result + summary."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from vmzrecon.discrepancy import DiscrepancyKind
from vmzrecon.schema import Wallet

if TYPE_CHECKING:
    from collections.abc import Iterable

    from vmzrecon.discrepancy import Discrepancy


@dataclass(frozen=True, slots=True)
class Summary:
    """Aggregate counts of a reconciliation result."""

    total: int
    by_kind: dict[DiscrepancyKind, int]
    by_wallet: dict[Wallet, int]
    net_vnd_missing: int
    """Sum of merchant_amount on MERCHANT_ONLY rows, minus
    wallet_amount on WALLET_ONLY rows. Positive = merchant claims
    more than wallet settled; negative = wallet settled more than
    merchant claims."""


def summarise(discrepancies: Iterable[Discrepancy]) -> Summary:
    by_kind: dict[DiscrepancyKind, int] = {k: 0 for k in DiscrepancyKind}
    by_wallet: dict[Wallet, int] = {w: 0 for w in Wallet}
    net = 0
    total = 0
    for d in discrepancies:
        total += 1
        by_kind[d.kind] += 1
        by_wallet[d.wallet] += 1
        if d.kind is DiscrepancyKind.MERCHANT_ONLY and d.merchant_amount is not None:
            net += d.merchant_amount
        elif d.kind is DiscrepancyKind.WALLET_ONLY and d.wallet_amount is not None:
            net -= d.wallet_amount
    return Summary(total=total, by_kind=by_kind, by_wallet=by_wallet, net_vnd_missing=net)


def format_text_report(discrepancies: Iterable[Discrepancy]) -> str:
    """Plain-text report — what ops sees in the daily Slack message."""
    items = list(discrepancies)
    s = summarise(items)
    lines: list[str] = []
    lines.append("=== Daily Wallet Reconciliation ===")
    lines.append(f"total discrepancies: {s.total}")
    lines.append(f"net VND missing (merchant - wallet): {s.net_vnd_missing:,}")
    lines.append("")
    lines.append("by kind:")
    for kind in DiscrepancyKind:
        lines.append(f"  {kind.value:<22} {s.by_kind[kind]:>6}")
    lines.append("")
    lines.append("by wallet:")
    for w in Wallet:
        lines.append(f"  {w.value:<10} {s.by_wallet[w]:>6}")
    if items:
        lines.append("")
        lines.append("details:")
        for d in items:
            lines.append(f"  [{d.kind.value}] {d.wallet.value} {d.order_id}: {d.detail}")
    return "\n".join(lines) + "\n"


def format_csv_report(discrepancies: Iterable[Discrepancy]) -> str:
    """CSV with one row per discrepancy — what gets attached to the ticket."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["kind", "wallet", "order_id", "wallet_amount_vnd", "merchant_amount_vnd", "detail"]
    )
    for d in discrepancies:
        writer.writerow(
            [
                d.kind.value,
                d.wallet.value,
                d.order_id,
                "" if d.wallet_amount is None else d.wallet_amount,
                "" if d.merchant_amount is None else d.merchant_amount,
                d.detail,
            ]
        )
    return buf.getvalue()


def format_json_report(discrepancies: Iterable[Discrepancy]) -> str:
    """Structured JSON — what gets shipped to the data warehouse."""
    items = list(discrepancies)
    s = summarise(items)
    payload = {
        "summary": {
            "total": s.total,
            "net_vnd_missing": s.net_vnd_missing,
            "by_kind": {k.value: v for k, v in s.by_kind.items()},
            "by_wallet": {w.value: v for w, v in s.by_wallet.items()},
        },
        "discrepancies": [
            {
                "kind": d.kind.value,
                "wallet": d.wallet.value,
                "order_id": d.order_id,
                "wallet_amount_vnd": d.wallet_amount,
                "merchant_amount_vnd": d.merchant_amount,
                "detail": d.detail,
            }
            for d in items
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


__all__ = [
    "Summary",
    "format_csv_report",
    "format_json_report",
    "format_text_report",
    "summarise",
]
