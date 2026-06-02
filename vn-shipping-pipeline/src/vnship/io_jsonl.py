"""JSONL codec for ShipmentResult."""

from __future__ import annotations

import json

from vnship.schema import (
    Carrier,
    ServiceType,
    ShipmentRequest,
    ShipmentResult,
    ZoneType,
)


def _req_str(d: object, key: str) -> str:
    if not isinstance(d, dict):
        raise TypeError("expected dict")
    v = d.get(key)
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v)}")
    return v


def _req_int(d: object, key: str) -> int:
    if not isinstance(d, dict):
        raise TypeError("expected dict")
    v = d.get(key)
    if not isinstance(v, int):
        raise TypeError(f"{key} must be int, got {type(v)}")
    return v


def _req_bool(d: object, key: str) -> bool:
    if not isinstance(d, dict):
        raise TypeError("expected dict")
    v = d.get(key)
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v)}")
    return v


def result_to_dict(r: ShipmentResult) -> dict[str, object]:
    req = r.request
    return {
        "carrier": req.carrier.value,
        "service": req.service.value,
        "zone": req.zone.value,
        "weight_g": req.weight_g,
        "declared_value_vnd": req.declared_value_vnd,
        "cod_amount_vnd": req.cod_amount_vnd,
        "is_fragile": req.is_fragile,
        "base_fee_vnd": r.base_fee_vnd,
        "weight_surcharge_vnd": r.weight_surcharge_vnd,
        "cod_fee_vnd": r.cod_fee_vnd,
        "fragile_surcharge_vnd": r.fragile_surcharge_vnd,
        "total_fee_vnd": r.total_fee_vnd,
    }


def result_from_dict(d: object) -> ShipmentResult:
    if not isinstance(d, dict):
        raise TypeError("expected dict")
    req = ShipmentRequest(
        carrier=Carrier(_req_str(d, "carrier")),
        service=ServiceType(_req_str(d, "service")),
        zone=ZoneType(_req_str(d, "zone")),
        weight_g=_req_int(d, "weight_g"),
        declared_value_vnd=_req_int(d, "declared_value_vnd"),
        cod_amount_vnd=_req_int(d, "cod_amount_vnd"),
        is_fragile=_req_bool(d, "is_fragile"),
    )
    return ShipmentResult(
        request=req,
        base_fee_vnd=_req_int(d, "base_fee_vnd"),
        weight_surcharge_vnd=_req_int(d, "weight_surcharge_vnd"),
        cod_fee_vnd=_req_int(d, "cod_fee_vnd"),
        fragile_surcharge_vnd=_req_int(d, "fragile_surcharge_vnd"),
        total_fee_vnd=_req_int(d, "total_fee_vnd"),
    )


def dump(results: list[ShipmentResult]) -> str:
    lines = [json.dumps(result_to_dict(r), ensure_ascii=False) for r in results]
    return "\n".join(lines) + ("\n" if lines else "")


def load(text: str) -> list[ShipmentResult]:
    out: list[ShipmentResult] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(result_from_dict(raw))
    return out
