"""Schema validation: CDR, RatedCDR, MonthlyBill."""

from __future__ import annotations

from datetime import datetime

import pytest

from cdrpipe.schema import (
    Carrier,
    CDRKind,
    MonthlyBill,
    PlanKind,
    RatedCDR,
)

from ._fixtures import make_cdr, voice_cdr

# ---------- CDR --------------------------------------------------------------


def test_cdr_kinds_complete():
    assert {k.value for k in CDRKind} == {"VOICE", "SMS", "DATA"}


def test_carriers_complete():
    assert {c.value for c in Carrier} == {
        "VIETTEL",
        "VINAPHONE",
        "MOBIFONE",
        "VIETNAMOBILE",
        "REDDI",
        "UNKNOWN",
    }


def test_plan_kinds_complete():
    assert {p.value for p in PlanKind} == {"PREPAID", "POSTPAID"}


def test_cdr_voice_basic():
    c = voice_cdr()
    assert c.kind is CDRKind.VOICE
    assert c.duration_seconds == 60


def test_cdr_rejects_empty_id():
    with pytest.raises(ValueError, match="cdr_id"):
        make_cdr(cdr_id="")


def test_cdr_rejects_empty_subscriber():
    with pytest.raises(ValueError, match="subscriber_msisdn"):
        make_cdr(subscriber_msisdn="")


def test_cdr_rejects_naive_datetime():
    with pytest.raises(ValueError, match="timezone-aware"):
        make_cdr(occurred_at=datetime(2026, 5, 18, 9, 0, 0))


def test_cdr_voice_requires_duration():
    with pytest.raises(ValueError, match="VOICE.*duration"):
        voice_cdr(duration_seconds=0)


def test_cdr_voice_rejects_data():
    """VOICE CDRs cannot have bytes_used or n_messages."""
    with pytest.raises(ValueError, match="VOICE.*bytes_used"):
        make_cdr(kind=CDRKind.VOICE, duration_seconds=60, bytes_used=100)


def test_cdr_sms_requires_messages():
    with pytest.raises(ValueError, match="SMS.*n_messages"):
        make_cdr(kind=CDRKind.SMS, duration_seconds=0, n_messages=0)


def test_cdr_data_requires_bytes():
    with pytest.raises(ValueError, match="DATA.*bytes_used"):
        make_cdr(kind=CDRKind.DATA, duration_seconds=0, bytes_used=0)


def test_cdr_rejects_negative_metrics():
    with pytest.raises(ValueError, match="duration_seconds"):
        voice_cdr(duration_seconds=-1)


# ---------- RatedCDR ---------------------------------------------------------


def test_rated_cdr_total_includes_vat():
    r = RatedCDR(
        cdr=voice_cdr(),
        subscriber_carrier=Carrier.VIETTEL,
        peer_carrier=Carrier.VINAPHONE,
        rated_amount_vnd=1_000,
        vat_amount_vnd=100,
        is_peak=True,
    )
    assert r.total_vnd == 1_100


def test_rated_cdr_rejects_negative():
    with pytest.raises(ValueError, match="rated_amount_vnd"):
        RatedCDR(
            cdr=voice_cdr(),
            subscriber_carrier=Carrier.VIETTEL,
            peer_carrier=Carrier.VINAPHONE,
            rated_amount_vnd=-1,
            vat_amount_vnd=0,
            is_peak=True,
        )


# ---------- MonthlyBill ------------------------------------------------------


def _bill(**overrides) -> MonthlyBill:  # type: ignore[no-untyped-def]
    defaults = {
        "subscriber_msisdn": "0961234567",
        "carrier": Carrier.VIETTEL,
        "plan_kind": PlanKind.PREPAID,
        "billing_month": "2026-05",
        "n_voice_cdrs": 10,
        "n_sms_cdrs": 5,
        "n_data_cdrs": 15,
        "total_voice_seconds": 600,
        "total_sms": 5,
        "total_bytes": 100 * 1024 * 1024,
        "pre_vat_amount_vnd": 50_000,
        "vat_amount_vnd": 5_000,
    }
    defaults.update(overrides)
    return MonthlyBill(**defaults)


def test_bill_total_amount_includes_vat():
    b = _bill()
    assert b.total_amount_vnd == 55_000


def test_bill_total_cdrs_sums():
    b = _bill(n_voice_cdrs=10, n_sms_cdrs=5, n_data_cdrs=15)
    assert b.total_cdrs == 30


def test_bill_rejects_negative_amount():
    with pytest.raises(ValueError, match="pre_vat_amount_vnd"):
        _bill(pre_vat_amount_vnd=-1)
