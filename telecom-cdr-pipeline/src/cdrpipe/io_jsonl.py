"""JSONL codec for CDR / RatedCDR / MonthlyBill / FraudFinding."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from cdrpipe.fraud import FraudFinding, FraudKind
from cdrpipe.schema import (
    CDR,
    Carrier,
    CDRKind,
    MonthlyBill,
    PlanKind,
    RatedCDR,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d[key]
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


# ---------- CDR -------------------------------------------------------------


def cdr_to_dict(c: CDR) -> dict[str, object]:
    return {
        "cdr_id": c.cdr_id,
        "subscriber_msisdn": c.subscriber_msisdn,
        "peer_msisdn": c.peer_msisdn,
        "kind": c.kind.value,
        "occurred_at": c.occurred_at.isoformat(),
        "duration_seconds": c.duration_seconds,
        "bytes_used": c.bytes_used,
        "n_messages": c.n_messages,
        "is_roaming": c.is_roaming,
        "is_premium": c.is_premium,
    }


def cdr_from_dict(d: dict[str, object]) -> CDR:
    return CDR(
        cdr_id=_require_str(d, "cdr_id"),
        subscriber_msisdn=_require_str(d, "subscriber_msisdn"),
        peer_msisdn=_require_str(d, "peer_msisdn") if "peer_msisdn" in d else "",
        kind=CDRKind(_require_str(d, "kind")),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        duration_seconds=_require_int(d, "duration_seconds") if "duration_seconds" in d else 0,
        bytes_used=_require_int(d, "bytes_used") if "bytes_used" in d else 0,
        n_messages=_require_int(d, "n_messages") if "n_messages" in d else 0,
        is_roaming=_require_bool(d, "is_roaming") if "is_roaming" in d else False,
        is_premium=_require_bool(d, "is_premium") if "is_premium" in d else False,
    )


# ---------- RatedCDR --------------------------------------------------------


def rated_to_dict(r: RatedCDR) -> dict[str, object]:
    return {
        "cdr": cdr_to_dict(r.cdr),
        "subscriber_carrier": r.subscriber_carrier.value,
        "peer_carrier": r.peer_carrier.value,
        "rated_amount_vnd": r.rated_amount_vnd,
        "vat_amount_vnd": r.vat_amount_vnd,
        "is_peak": r.is_peak,
    }


def rated_from_dict(d: dict[str, object]) -> RatedCDR:
    cdr_raw = d["cdr"]
    if not isinstance(cdr_raw, dict):
        raise TypeError("cdr must be dict")
    return RatedCDR(
        cdr=cdr_from_dict(cdr_raw),
        subscriber_carrier=Carrier(_require_str(d, "subscriber_carrier")),
        peer_carrier=Carrier(_require_str(d, "peer_carrier")),
        rated_amount_vnd=_require_int(d, "rated_amount_vnd"),
        vat_amount_vnd=_require_int(d, "vat_amount_vnd"),
        is_peak=_require_bool(d, "is_peak"),
    )


# ---------- MonthlyBill -----------------------------------------------------


def bill_to_dict(b: MonthlyBill) -> dict[str, object]:
    return {
        "subscriber_msisdn": b.subscriber_msisdn,
        "carrier": b.carrier.value,
        "plan_kind": b.plan_kind.value,
        "billing_month": b.billing_month,
        "n_voice_cdrs": b.n_voice_cdrs,
        "n_sms_cdrs": b.n_sms_cdrs,
        "n_data_cdrs": b.n_data_cdrs,
        "total_voice_seconds": b.total_voice_seconds,
        "total_sms": b.total_sms,
        "total_bytes": b.total_bytes,
        "pre_vat_amount_vnd": b.pre_vat_amount_vnd,
        "vat_amount_vnd": b.vat_amount_vnd,
    }


def bill_from_dict(d: dict[str, object]) -> MonthlyBill:
    return MonthlyBill(
        subscriber_msisdn=_require_str(d, "subscriber_msisdn"),
        carrier=Carrier(_require_str(d, "carrier")),
        plan_kind=PlanKind(_require_str(d, "plan_kind")),
        billing_month=_require_str(d, "billing_month"),
        n_voice_cdrs=_require_int(d, "n_voice_cdrs"),
        n_sms_cdrs=_require_int(d, "n_sms_cdrs"),
        n_data_cdrs=_require_int(d, "n_data_cdrs"),
        total_voice_seconds=_require_int(d, "total_voice_seconds"),
        total_sms=_require_int(d, "total_sms"),
        total_bytes=_require_int(d, "total_bytes"),
        pre_vat_amount_vnd=_require_int(d, "pre_vat_amount_vnd"),
        vat_amount_vnd=_require_int(d, "vat_amount_vnd"),
    )


# ---------- FraudFinding ----------------------------------------------------


def fraud_to_dict(f: FraudFinding) -> dict[str, object]:
    return {
        "kind": f.kind.value,
        "subscriber_msisdn": f.subscriber_msisdn,
        "carrier": f.carrier.value,
        "detail": f.detail,
        "metric": f.metric,
    }


def fraud_from_dict(d: dict[str, object]) -> FraudFinding:
    return FraudFinding(
        kind=FraudKind(_require_str(d, "kind")),
        subscriber_msisdn=_require_str(d, "subscriber_msisdn"),
        carrier=Carrier(_require_str(d, "carrier")),
        detail=_require_str(d, "detail"),
        metric=_require_int(d, "metric"),
    )


# ---------- dump / load -----------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_cdrs(items: Iterable[CDR]) -> str:
    return _dump(cdr_to_dict(c) for c in items)


def dump_rated(items: Iterable[RatedCDR]) -> str:
    return _dump(rated_to_dict(r) for r in items)


def dump_bills(items: Iterable[MonthlyBill]) -> str:
    return _dump(bill_to_dict(b) for b in items)


def dump_frauds(items: Iterable[FraudFinding]) -> str:
    return _dump(fraud_to_dict(f) for f in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_cdrs(text: str) -> list[CDR]:
    return [cdr_from_dict(d) for d in _iter_lines(text)]


def load_rated(text: str) -> list[RatedCDR]:
    return [rated_from_dict(d) for d in _iter_lines(text)]


def load_bills(text: str) -> list[MonthlyBill]:
    return [bill_from_dict(d) for d in _iter_lines(text)]


def load_frauds(text: str) -> list[FraudFinding]:
    return [fraud_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "bill_from_dict",
    "bill_to_dict",
    "cdr_from_dict",
    "cdr_to_dict",
    "dump_bills",
    "dump_cdrs",
    "dump_frauds",
    "dump_rated",
    "fraud_from_dict",
    "fraud_to_dict",
    "load_bills",
    "load_cdrs",
    "load_frauds",
    "load_rated",
    "rated_from_dict",
    "rated_to_dict",
]
