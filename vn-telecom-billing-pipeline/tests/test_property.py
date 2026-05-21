"""Property-based tests for VN telecom billing."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vntelecom.billing import _billing_minutes, bill
from vntelecom.schema import CDR, CallType, Operator, ServiceType


def _make_cdr(duration: int, svc: ServiceType, prepaid: bool) -> CDR:
    return CDR(
        cdr_id="X",
        subscriber_msisdn="0901234567",
        operator=Operator.VIETTEL,
        service_type=svc,
        call_type=CallType.ON_NET,
        duration_seconds=duration,
        timestamp_epoch_s=1_748_700_001,
        destination_msisdn="",
        is_prepaid=prepaid,
    )


@given(st.integers(min_value=0, max_value=3600))
@settings(max_examples=50)
def test_billing_minutes_always_ge_seconds_div_60(seconds: int) -> None:
    mins = _billing_minutes(seconds)
    assert mins >= seconds / 60.0 - 1e-9


@given(
    duration=st.integers(min_value=0, max_value=10_000),
    is_prepaid=st.booleans(),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_total_charge_ge_base_for_voice(duration: int, is_prepaid: bool) -> None:
    cdr = _make_cdr(duration, ServiceType.VOICE, is_prepaid)
    b = bill(cdr)
    assert b.total_charge_vnd >= b.base_charge_vnd


@given(st.integers(min_value=0, max_value=100_000))
@settings(max_examples=40)
def test_data_charge_proportional_to_kb(kb: int) -> None:
    cdr = _make_cdr(kb, ServiceType.DATA, True)
    b = bill(cdr)
    assert b.base_charge_vnd == pytest.approx(5.0 * kb, rel=1e-6)


@given(
    duration=st.integers(min_value=1, max_value=3600),
)
@settings(max_examples=30)
def test_vat_exactly_ten_percent(duration: int) -> None:
    cdr = _make_cdr(duration, ServiceType.VOICE, True)
    b = bill(cdr)
    assert b.vat_vnd == pytest.approx(b.base_charge_vnd * 0.10, rel=1e-4)


@given(
    duration=st.integers(min_value=0, max_value=3600),
    is_prepaid=st.booleans(),
)
@settings(max_examples=40)
def test_total_equals_base_plus_vat(duration: int, is_prepaid: bool) -> None:
    cdr = _make_cdr(duration, ServiceType.VOICE, is_prepaid)
    b = bill(cdr)
    assert b.total_charge_vnd == pytest.approx(b.base_charge_vnd + b.vat_vnd, rel=1e-5)
