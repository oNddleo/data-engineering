"""Vietnam telecom CDR billing engine.

Rate schedule (VND, as of 2024 — illustrative, not regulatory):
  Voice:
    On-net:         550 VND/min (prepaid), 450 VND/min (postpaid)
    Off-net:        980 VND/min
    International: 4,500 VND/min
    Roaming out:   15,000 VND/min
    Landline:      700 VND/min
  SMS:
    On-net:         350 VND/SMS (prepaid), 300 VND/SMS (postpaid)
    Off-net:        800 VND/SMS
    International: 3,500 VND/SMS
  MMS:             1,500 VND/MMS
  Data:            5 VND/KB (on-demand), with 4G plans at 3 VND/KB
  Premium SMS:    15,000 VND/SMS

VAT: 10%
Billing unit: 6-second increments for voice (ceiling).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from vntelecom.schema import CDR, CallType, Operator, ServiceType

_VAT_RATE = 0.10

# ---- Voice rates (VND/min) --------------------------------------------------

_VOICE_RATE_PREPAID: dict[CallType, float] = {
    CallType.ON_NET: 550.0,
    CallType.OFF_NET: 980.0,
    CallType.LANDLINE: 700.0,
    CallType.INTERNATIONAL: 4_500.0,
    CallType.ROAMING_IN: 0.0,  # roaming-in charged to visitor's operator
    CallType.ROAMING_OUT: 15_000.0,
}

_VOICE_RATE_POSTPAID: dict[CallType, float] = {
    CallType.ON_NET: 450.0,
    CallType.OFF_NET: 980.0,
    CallType.LANDLINE: 700.0,
    CallType.INTERNATIONAL: 4_500.0,
    CallType.ROAMING_IN: 0.0,
    CallType.ROAMING_OUT: 15_000.0,
}

# ---- SMS rates (VND/message) ------------------------------------------------

_SMS_RATE_PREPAID: dict[CallType, float] = {
    CallType.ON_NET: 350.0,
    CallType.OFF_NET: 800.0,
    CallType.INTERNATIONAL: 3_500.0,
    CallType.LANDLINE: 800.0,
    CallType.ROAMING_IN: 0.0,
    CallType.ROAMING_OUT: 3_500.0,
}

_SMS_RATE_POSTPAID: dict[CallType, float] = {
    CallType.ON_NET: 300.0,
    CallType.OFF_NET: 800.0,
    CallType.INTERNATIONAL: 3_500.0,
    CallType.LANDLINE: 800.0,
    CallType.ROAMING_IN: 0.0,
    CallType.ROAMING_OUT: 3_500.0,
}

# ---- Data rates (VND/KB) ---------------------------------------------------

_DATA_RATE_PER_KB: dict[Operator, float] = {
    Operator.VIETTEL: 5.0,
    Operator.MOBIFONE: 5.0,
    Operator.VINAPHONE: 5.0,
    Operator.VIETNAMOBILE: 4.0,
    Operator.GMOBILE: 4.0,
}

_DATA_RATE_4G_PER_KB: float = 3.0  # 4G plan discounted rate

# ---- MMS & Premium ---------------------------------------------------------

_MMS_RATE: float = 1_500.0
_PREMIUM_SMS_RATE: float = 15_000.0


def _billing_minutes(duration_seconds: int) -> float:
    """Convert seconds to billing minutes using 6-second ceiling increments."""
    if duration_seconds <= 0:
        return 0.0
    increments = math.ceil(duration_seconds / 6)
    return increments * 6 / 60.0


def _voice_charge(cdr: CDR) -> float:
    rate_table = _VOICE_RATE_PREPAID if cdr.is_prepaid else _VOICE_RATE_POSTPAID
    rate = rate_table.get(cdr.call_type, _VOICE_RATE_PREPAID[CallType.OFF_NET])
    minutes = _billing_minutes(cdr.duration_seconds)
    return rate * minutes


def _sms_charge(cdr: CDR) -> float:
    rate_table = _SMS_RATE_PREPAID if cdr.is_prepaid else _SMS_RATE_POSTPAID
    return rate_table.get(cdr.call_type, _SMS_RATE_PREPAID[CallType.OFF_NET])


def _data_charge(cdr: CDR) -> float:
    kb = cdr.duration_seconds  # data CDRs use duration_seconds as KB
    rate = _DATA_RATE_PER_KB.get(cdr.operator, 5.0)
    return rate * kb


@dataclass(frozen=True, slots=True)
class BilledCDR:
    """CDR after billing calculation."""

    cdr_id: str
    subscriber_msisdn: str
    operator: Operator
    service_type: ServiceType
    call_type: CallType
    duration_seconds: int
    timestamp_epoch_s: int
    base_charge_vnd: float  # before VAT
    vat_vnd: float
    total_charge_vnd: float  # base + VAT
    billing_unit: str  # "min" / "msg" / "KB"


def bill(cdr: CDR) -> BilledCDR:
    """Compute billing for a single CDR."""
    svc = cdr.service_type

    if svc == ServiceType.VOICE:
        base = _voice_charge(cdr)
        unit = "min"
    elif svc == ServiceType.SMS:
        base = _sms_charge(cdr)
        unit = "msg"
    elif svc == ServiceType.MMS:
        base = _MMS_RATE
        unit = "msg"
    elif svc == ServiceType.DATA:
        base = _data_charge(cdr)
        unit = "KB"
    else:  # PREMIUM
        base = _PREMIUM_SMS_RATE
        unit = "msg"

    vat = base * _VAT_RATE
    total = base + vat

    return BilledCDR(
        cdr_id=cdr.cdr_id,
        subscriber_msisdn=cdr.subscriber_msisdn,
        operator=cdr.operator,
        service_type=svc,
        call_type=cdr.call_type,
        duration_seconds=cdr.duration_seconds,
        timestamp_epoch_s=cdr.timestamp_epoch_s,
        base_charge_vnd=round(base, 2),
        vat_vnd=round(vat, 2),
        total_charge_vnd=round(total, 2),
        billing_unit=unit,
    )
