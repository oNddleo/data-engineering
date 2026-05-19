"""Billing aggregation: per-subscriber, per-month rollups."""

from __future__ import annotations

from datetime import datetime

from cdrpipe.billing import aggregate_bills
from cdrpipe.rating import rate
from cdrpipe.schema import VN_TZ, Carrier, PlanKind

from ._fixtures import data_cdr, sms_cdr, voice_cdr


def test_aggregate_groups_by_subscriber() -> None:
    rcs = [rate(voice_cdr(cdr_id=f"V-{i}", duration_seconds=60)) for i in range(3)]
    bills = aggregate_bills(rcs)
    assert len(bills) == 1
    assert bills[0].n_voice_cdrs == 3
    assert bills[0].total_voice_seconds == 180


def test_aggregate_groups_by_month() -> None:
    """CDRs in different months produce two bills for the same subscriber."""
    rcs = [
        rate(
            voice_cdr(
                cdr_id="V-may",
                at=datetime(2026, 5, 18, 10, 0, tzinfo=VN_TZ),
            )
        ),
        rate(
            voice_cdr(
                cdr_id="V-jun",
                at=datetime(2026, 6, 1, 10, 0, tzinfo=VN_TZ),
            )
        ),
    ]
    bills = aggregate_bills(rcs)
    assert len(bills) == 2
    assert {b.billing_month for b in bills} == {"2026-05", "2026-06"}


def test_aggregate_late_arriving_cdr_goes_to_prior_month() -> None:
    """A CDR for April that arrives during May processing bills into April."""
    rcs = [
        rate(
            voice_cdr(
                cdr_id="V-apr",
                at=datetime(2026, 4, 30, 23, 30, tzinfo=VN_TZ),
            )
        ),
        rate(
            voice_cdr(
                cdr_id="V-may",
                at=datetime(2026, 5, 1, 0, 30, tzinfo=VN_TZ),
            )
        ),
    ]
    bills = aggregate_bills(rcs)
    months = {b.billing_month for b in bills}
    assert "2026-04" in months and "2026-05" in months


def test_aggregate_mixed_kinds() -> None:
    rcs = [
        rate(voice_cdr(cdr_id="V-1")),
        rate(sms_cdr(cdr_id="S-1")),
        rate(data_cdr(cdr_id="D-1", bytes_used=5 * 1024 * 1024)),
    ]
    bills = aggregate_bills(rcs)
    assert len(bills) == 1
    b = bills[0]
    assert b.n_voice_cdrs == 1
    assert b.n_sms_cdrs == 1
    assert b.n_data_cdrs == 1
    assert b.total_bytes == 5 * 1024 * 1024


def test_aggregate_plan_kind_defaults_to_prepaid() -> None:
    rcs = [rate(voice_cdr())]
    bills = aggregate_bills(rcs)
    assert bills[0].plan_kind is PlanKind.PREPAID


def test_aggregate_plan_kind_lookup() -> None:
    rcs = [rate(voice_cdr(subscriber="0961234567"))]
    bills = aggregate_bills(
        rcs,
        plan_kind_by_msisdn={"0961234567": PlanKind.POSTPAID},
    )
    assert bills[0].plan_kind is PlanKind.POSTPAID


def test_aggregate_carrier_resolved() -> None:
    rcs = [rate(voice_cdr(subscriber="0961234567"))]
    bills = aggregate_bills(rcs)
    assert bills[0].carrier is Carrier.VIETTEL


def test_aggregate_amount_matches_sum() -> None:
    """Bill totals must exactly sum the rated CDR amounts."""
    rcs = [
        rate(voice_cdr(cdr_id="V-1", duration_seconds=60)),
        rate(voice_cdr(cdr_id="V-2", duration_seconds=120)),
        rate(sms_cdr(cdr_id="S-1")),
    ]
    bills = aggregate_bills(rcs)
    pre_vat = sum(r.rated_amount_vnd for r in rcs)
    vat = sum(r.vat_amount_vnd for r in rcs)
    assert bills[0].pre_vat_amount_vnd == pre_vat
    assert bills[0].vat_amount_vnd == vat
    assert bills[0].total_amount_vnd == pre_vat + vat


def test_aggregate_sorted_by_month_then_msisdn() -> None:
    rcs = [
        rate(voice_cdr(cdr_id="V-1", subscriber="0971234567")),
        rate(voice_cdr(cdr_id="V-2", subscriber="0961234567")),
    ]
    bills = aggregate_bills(rcs)
    assert [b.subscriber_msisdn for b in bills] == ["0961234567", "0971234567"]


def test_aggregate_empty_returns_empty() -> None:
    assert aggregate_bills([]) == []
