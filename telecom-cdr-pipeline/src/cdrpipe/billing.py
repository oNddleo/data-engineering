"""Monthly billing aggregation per subscriber.

Takes a stream of ``RatedCDR``s (typically a month's worth) and
produces one ``MonthlyBill`` per (subscriber, billing month). The
billing month is the ``YYYY-MM`` of the CDR's local-VN-time
``occurred_at`` — late-arriving CDRs for a prior month are billed
into that prior month, not the current one.

Postpaid vs prepaid is captured separately on each subscriber's
``plan_kind``; this module just produces the aggregate. The plan
kind is passed in as a dict (subscriber → ``PlanKind``).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from cdrpipe.schema import CDRKind, MonthlyBill, PlanKind

if TYPE_CHECKING:
    from cdrpipe.schema import RatedCDR


def aggregate_bills(
    rated_cdrs: list[RatedCDR],
    *,
    plan_kind_by_msisdn: dict[str, PlanKind] | None = None,
) -> list[MonthlyBill]:
    """Aggregate ``rated_cdrs`` into per-subscriber, per-month bills.

    Output sorted by ``(billing_month, subscriber_msisdn)``.
    """
    plan_kinds = plan_kind_by_msisdn or {}
    groups: dict[tuple[str, str], list[RatedCDR]] = defaultdict(list)
    for rc in rated_cdrs:
        key = (rc.cdr.subscriber_msisdn, _billing_month_for(rc))
        groups[key].append(rc)

    out: list[MonthlyBill] = []
    for (msisdn, month), group in groups.items():
        n_voice = sum(1 for r in group if r.cdr.kind is CDRKind.VOICE)
        n_sms = sum(1 for r in group if r.cdr.kind is CDRKind.SMS)
        n_data = sum(1 for r in group if r.cdr.kind is CDRKind.DATA)
        total_voice_seconds = sum(
            r.cdr.duration_seconds for r in group if r.cdr.kind is CDRKind.VOICE
        )
        total_sms = sum(r.cdr.n_messages for r in group if r.cdr.kind is CDRKind.SMS)
        total_bytes = sum(r.cdr.bytes_used for r in group if r.cdr.kind is CDRKind.DATA)
        pre_vat = sum(r.rated_amount_vnd for r in group)
        vat = sum(r.vat_amount_vnd for r in group)
        out.append(
            MonthlyBill(
                subscriber_msisdn=msisdn,
                carrier=group[0].subscriber_carrier,
                plan_kind=plan_kinds.get(msisdn, PlanKind.PREPAID),
                billing_month=month,
                n_voice_cdrs=n_voice,
                n_sms_cdrs=n_sms,
                n_data_cdrs=n_data,
                total_voice_seconds=total_voice_seconds,
                total_sms=total_sms,
                total_bytes=total_bytes,
                pre_vat_amount_vnd=pre_vat,
                vat_amount_vnd=vat,
            )
        )
    out.sort(key=lambda b: (b.billing_month, b.subscriber_msisdn))
    return out


def _billing_month_for(rc: RatedCDR) -> str:
    """Return ``YYYY-MM`` for the rated CDR's local-VN-time month."""
    dt = rc.cdr.occurred_at
    return f"{dt.year:04d}-{dt.month:02d}"


__all__ = ["aggregate_bills"]
