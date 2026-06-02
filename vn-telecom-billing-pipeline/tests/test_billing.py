"""Tests for VN telecom CDR billing engine."""

from __future__ import annotations

import pytest

from vntelecom.billing import _billing_minutes, bill
from vntelecom.schema import CDR, CallType, Operator, ServiceType


def _make_cdr(
    service_type: ServiceType = ServiceType.VOICE,
    call_type: CallType = CallType.ON_NET,
    duration: int = 60,
    is_prepaid: bool = True,
) -> CDR:
    return CDR(
        cdr_id="CDR-001",
        subscriber_msisdn="0901234567",
        operator=Operator.VIETTEL,
        service_type=service_type,
        call_type=call_type,
        duration_seconds=duration,
        timestamp_epoch_s=1_748_700_000,
        destination_msisdn="0987654321",
        is_prepaid=is_prepaid,
    )


class TestBillingMinutes:
    def test_exactly_one_minute(self) -> None:
        assert _billing_minutes(60) == pytest.approx(1.0)

    def test_zero_returns_zero(self) -> None:
        assert _billing_minutes(0) == 0.0

    def test_6_seconds_is_one_increment(self) -> None:
        assert _billing_minutes(6) == pytest.approx(6 / 60)

    def test_7_seconds_rounds_up_to_12(self) -> None:
        assert _billing_minutes(7) == pytest.approx(12 / 60)

    def test_ceiling_increments(self) -> None:
        # 1 second → 6 second billing increment
        assert _billing_minutes(1) == pytest.approx(6 / 60)


class TestVoiceBilling:
    def test_on_net_prepaid_1min(self) -> None:
        cdr = _make_cdr(duration=60, is_prepaid=True)
        b = bill(cdr)
        assert b.base_charge_vnd == pytest.approx(550.0)
        assert b.billing_unit == "min"

    def test_on_net_postpaid_cheaper(self) -> None:
        prepaid = bill(_make_cdr(duration=60, is_prepaid=True))
        postpaid = bill(_make_cdr(duration=60, is_prepaid=False))
        assert postpaid.base_charge_vnd < prepaid.base_charge_vnd

    def test_off_net_more_expensive_than_on_net(self) -> None:
        on_net = bill(_make_cdr(call_type=CallType.ON_NET, duration=60))
        off_net = bill(_make_cdr(call_type=CallType.OFF_NET, duration=60))
        assert off_net.base_charge_vnd > on_net.base_charge_vnd

    def test_international_most_expensive(self) -> None:
        domestic = bill(_make_cdr(call_type=CallType.OFF_NET, duration=60))
        intl = bill(_make_cdr(call_type=CallType.INTERNATIONAL, duration=60))
        assert intl.base_charge_vnd > domestic.base_charge_vnd

    def test_vat_is_ten_percent(self) -> None:
        b = bill(_make_cdr(duration=60))
        assert b.vat_vnd == pytest.approx(b.base_charge_vnd * 0.10, rel=1e-4)

    def test_total_equals_base_plus_vat(self) -> None:
        b = bill(_make_cdr(duration=60))
        assert b.total_charge_vnd == pytest.approx(b.base_charge_vnd + b.vat_vnd, rel=1e-6)

    def test_zero_duration_zero_charge(self) -> None:
        cdr = _make_cdr(duration=0)
        b = bill(cdr)
        assert b.base_charge_vnd == 0.0
        assert b.total_charge_vnd == 0.0

    def test_roaming_in_is_free(self) -> None:
        cdr = _make_cdr(call_type=CallType.ROAMING_IN, duration=60)
        b = bill(cdr)
        assert b.base_charge_vnd == 0.0


class TestSMSBilling:
    def test_sms_on_net_prepaid(self) -> None:
        cdr = _make_cdr(service_type=ServiceType.SMS, call_type=CallType.ON_NET, duration=1)
        b = bill(cdr)
        assert b.base_charge_vnd == pytest.approx(350.0)
        assert b.billing_unit == "msg"

    def test_sms_off_net_more_expensive(self) -> None:
        on_net = bill(_make_cdr(ServiceType.SMS, CallType.ON_NET, 1))
        off_net = bill(_make_cdr(ServiceType.SMS, CallType.OFF_NET, 1))
        assert off_net.base_charge_vnd > on_net.base_charge_vnd

    def test_sms_postpaid_cheaper_than_prepaid(self) -> None:
        prepaid = bill(_make_cdr(ServiceType.SMS, CallType.ON_NET, 1, is_prepaid=True))
        postpaid = bill(_make_cdr(ServiceType.SMS, CallType.ON_NET, 1, is_prepaid=False))
        assert postpaid.base_charge_vnd <= prepaid.base_charge_vnd


class TestDataBilling:
    def test_data_charge_per_kb(self) -> None:
        cdr = CDR(
            cdr_id="CDR-D01",
            subscriber_msisdn="0901234567",
            operator=Operator.VIETTEL,
            service_type=ServiceType.DATA,
            call_type=CallType.ON_NET,
            duration_seconds=1024,  # 1024 KB = 1 MB
            timestamp_epoch_s=1_748_700_000,
            destination_msisdn="",
            is_prepaid=True,
        )
        b = bill(cdr)
        assert b.base_charge_vnd == pytest.approx(5.0 * 1024, rel=1e-4)
        assert b.billing_unit == "KB"


class TestMMSBilling:
    def test_mms_fixed_rate(self) -> None:
        cdr = _make_cdr(service_type=ServiceType.MMS, duration=1)
        b = bill(cdr)
        assert b.base_charge_vnd == pytest.approx(1_500.0)
        assert b.billing_unit == "msg"


class TestValidation:
    def test_empty_cdr_id_raises(self) -> None:
        with pytest.raises(ValueError):
            CDR(
                cdr_id="",
                subscriber_msisdn="0901234567",
                operator=Operator.VIETTEL,
                service_type=ServiceType.VOICE,
                call_type=CallType.ON_NET,
                duration_seconds=60,
                timestamp_epoch_s=1_748_700_000,
                destination_msisdn="",
                is_prepaid=True,
            )

    def test_negative_duration_raises(self) -> None:
        with pytest.raises(ValueError):
            _make_cdr(duration=-1)
