"""Simulate VN telecom CDR streams."""

from __future__ import annotations

import random

from vntelecom.schema import CDR, CallType, Operator, ServiceType

_VN_PREFIXES = ["090", "091", "092", "093", "094", "095", "096", "097", "098"]


def _random_msisdn(rng: random.Random) -> str:
    prefix = rng.choice(_VN_PREFIXES)
    suffix = str(rng.randint(1_000_000, 9_999_999))
    return f"{prefix}{suffix}"


def simulate_cdrs(
    n: int = 200,
    seed: int = 42,
    base_epoch_s: int = 1_748_700_000,
) -> list[CDR]:
    """Generate *n* synthetic CDRs."""
    rng = random.Random(seed)
    operators = list(Operator)
    service_types = [
        ServiceType.VOICE,
        ServiceType.VOICE,
        ServiceType.VOICE,  # weighted 3:1:1:1
        ServiceType.SMS,
        ServiceType.DATA,
        ServiceType.MMS,
    ]
    call_types = [
        CallType.ON_NET,
        CallType.ON_NET,
        CallType.OFF_NET,
        CallType.LANDLINE,
        CallType.INTERNATIONAL,
        CallType.ROAMING_OUT,
    ]
    cdrs: list[CDR] = []

    for i in range(n):
        svc = rng.choice(service_types)
        ct = rng.choice(call_types)
        if svc == ServiceType.VOICE:
            duration = rng.randint(5, 1800)  # 5s to 30min
        elif svc == ServiceType.DATA:
            duration = rng.randint(100, 100_000)  # KB
        else:
            duration = 1  # 1 message

        cdrs.append(
            CDR(
                cdr_id=f"CDR-{i:06d}",
                subscriber_msisdn=_random_msisdn(rng),
                operator=rng.choice(operators),
                service_type=svc,
                call_type=ct,
                duration_seconds=duration,
                timestamp_epoch_s=base_epoch_s + rng.randint(0, 86_400),
                destination_msisdn=_random_msisdn(rng) if svc != ServiceType.DATA else "",
                is_prepaid=rng.choice([True, False]),
            )
        )
    return cdrs
