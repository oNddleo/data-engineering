"""Reports — regulator-format CSV + JSON summaries.

The CSV columns are tuned for the SBV monthly compliance template:
exactly one row per audited transaction, with the trigger kinds
joined by ``|``. Banks ship this file (signed + sealed with the
Merkle root of the period) to the SBV portal.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sbv2345.ledger import SealedAuditRecord


REGULATOR_CSV_COLUMNS: tuple[str, ...] = (
    "sequence_number",
    "txn_id",
    "occurred_at",
    "initiator_account",
    "initiator_bank_bin",
    "beneficiary_account",
    "beneficiary_bank_bin",
    "amount_vnd",
    "channel",
    "auth_method",
    "biometric_method",
    "cross_border",
    "triggered_kinds",
    "daily_cumulative_after_vnd",
    "record_hash",
    "prev_hash",
    "sealed_at",
)


def regulator_csv(records: Iterable[SealedAuditRecord]) -> str:
    """Render records as the regulator-format CSV."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(REGULATOR_CSV_COLUMNS)
    for r in records:
        t = r.event.txn
        w.writerow(
            [
                r.sequence_number,
                t.txn_id,
                t.occurred_at.isoformat(),
                t.initiator_account,
                t.initiator_bank_bin,
                t.beneficiary_account,
                t.beneficiary_bank_bin,
                t.amount_vnd,
                t.channel.value,
                t.auth_method.value,
                "" if t.biometric_method is None else t.biometric_method.value,
                str(t.cross_border).lower(),
                "|".join(k.value for k in r.event.triggered_kinds),
                r.event.daily_cumulative_after_vnd,
                r.record_hash,
                r.prev_hash,
                r.sealed_at.isoformat(),
            ]
        )
    return buf.getvalue()


@dataclass(frozen=True, slots=True)
class ReportSummary:
    """Aggregate counts across an audit period."""

    total: int
    by_trigger: dict[str, int] = field(default_factory=dict)
    by_channel: dict[str, int] = field(default_factory=dict)
    by_auth_method: dict[str, int] = field(default_factory=dict)
    total_value_vnd: int = 0
    biometric_verified_count: int = 0
    cross_border_count: int = 0


def summarise(records: Iterable[SealedAuditRecord]) -> ReportSummary:
    total = 0
    by_trigger: dict[str, int] = {}
    by_channel: dict[str, int] = {}
    by_auth: dict[str, int] = {}
    value = 0
    bio = 0
    cross = 0
    for r in records:
        t = r.event.txn
        total += 1
        for k in r.event.triggered_kinds:
            by_trigger[k.value] = by_trigger.get(k.value, 0) + 1
        by_channel[t.channel.value] = by_channel.get(t.channel.value, 0) + 1
        by_auth[t.auth_method.value] = by_auth.get(t.auth_method.value, 0) + 1
        value += t.amount_vnd
        if t.auth_method.value == "BIOMETRIC":
            bio += 1
        if t.cross_border:
            cross += 1
    return ReportSummary(
        total=total,
        by_trigger=by_trigger,
        by_channel=by_channel,
        by_auth_method=by_auth,
        total_value_vnd=value,
        biometric_verified_count=bio,
        cross_border_count=cross,
    )


__all__ = ["REGULATOR_CSV_COLUMNS", "ReportSummary", "regulator_csv", "summarise"]
