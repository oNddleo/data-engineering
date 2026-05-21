"""JSONL codec for VN telecom CDRs."""

from __future__ import annotations

import json

from vntelecom.billing import BilledCDR, bill
from vntelecom.schema import CDR, CallType, Operator, ServiceType


def cdr_to_dict(c: CDR) -> dict[str, object]:
    return {
        "cdr_id": c.cdr_id,
        "subscriber_msisdn": c.subscriber_msisdn,
        "operator": c.operator.value,
        "service_type": c.service_type.value,
        "call_type": c.call_type.value,
        "duration_seconds": c.duration_seconds,
        "timestamp_epoch_s": c.timestamp_epoch_s,
        "destination_msisdn": c.destination_msisdn,
        "is_prepaid": c.is_prepaid,
    }


def billed_to_dict(b: BilledCDR) -> dict[str, object]:
    return {
        "cdr_id": b.cdr_id,
        "subscriber_msisdn": b.subscriber_msisdn,
        "operator": b.operator.value,
        "service_type": b.service_type.value,
        "call_type": b.call_type.value,
        "duration_seconds": b.duration_seconds,
        "timestamp_epoch_s": b.timestamp_epoch_s,
        "base_charge_vnd": b.base_charge_vnd,
        "vat_vnd": b.vat_vnd,
        "total_charge_vnd": b.total_charge_vnd,
        "billing_unit": b.billing_unit,
    }


def _req_str(d: dict[str, object], k: str) -> str:
    v = d.get(k)
    if not isinstance(v, str):
        raise TypeError(f"{k} must be str")
    return v


def _req_int(d: dict[str, object], k: str) -> int:
    v = d.get(k, 0)
    if not isinstance(v, int):
        raise TypeError(f"{k} must be int")
    return v


def _req_bool(d: dict[str, object], k: str) -> bool:
    v = d.get(k, False)
    if not isinstance(v, bool):
        raise TypeError(f"{k} must be bool")
    return v


def cdr_from_dict(d: object) -> CDR:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")
    return CDR(
        cdr_id=_req_str(d, "cdr_id"),
        subscriber_msisdn=_req_str(d, "subscriber_msisdn"),
        operator=Operator(_req_str(d, "operator")),
        service_type=ServiceType(_req_str(d, "service_type")),
        call_type=CallType(_req_str(d, "call_type")),
        duration_seconds=_req_int(d, "duration_seconds"),
        timestamp_epoch_s=_req_int(d, "timestamp_epoch_s"),
        destination_msisdn=_req_str(d, "destination_msisdn"),
        is_prepaid=_req_bool(d, "is_prepaid"),
    )


def dump_cdrs(cdrs: list[CDR]) -> str:
    lines = [json.dumps(cdr_to_dict(c), ensure_ascii=False) for c in cdrs]
    return "\n".join(lines) + ("\n" if lines else "")


def dump_billed(billed: list[BilledCDR]) -> str:
    lines = [json.dumps(billed_to_dict(b), ensure_ascii=False) for b in billed]
    return "\n".join(lines) + ("\n" if lines else "")


def load_and_bill(text: str) -> list[BilledCDR]:
    out: list[BilledCDR] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        out.append(bill(cdr_from_dict(raw)))
    return out
