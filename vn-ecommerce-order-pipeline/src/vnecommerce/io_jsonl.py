"""JSONL codec for VN e-commerce orders."""

from __future__ import annotations

import json

from vnecommerce.normaliser import NormalisedOrder, normalise
from vnecommerce.schema import Platform, RawOrder


def raw_order_to_dict(r: RawOrder) -> dict[str, object]:
    return {
        "platform": r.platform.value,
        "platform_order_id": r.platform_order_id,
        "raw_status": r.raw_status,
        "raw_payment": r.raw_payment,
        "raw_shipping": r.raw_shipping,
        "item_total_vnd": r.item_total_vnd,
        "shipping_fee_vnd": r.shipping_fee_vnd,
        "platform_discount_vnd": r.platform_discount_vnd,
        "seller_discount_vnd": r.seller_discount_vnd,
        "buyer_paid_vnd": r.buyer_paid_vnd,
        "seller_receives_vnd": r.seller_receives_vnd,
        "tracking_number": r.tracking_number,
        "estimated_delivery_date": r.estimated_delivery_date,
        "buyer_province": r.buyer_province,
        "seller_province": r.seller_province,
    }


def normalised_order_to_dict(n: NormalisedOrder) -> dict[str, object]:
    return {
        "platform": n.platform.value,
        "platform_order_id": n.platform_order_id,
        "status": n.status.value,
        "payment_method": n.payment_method.value,
        "shipping_method": n.shipping_method.value,
        "item_total_vnd": n.item_total_vnd,
        "shipping_fee_vnd": n.shipping_fee_vnd,
        "total_discount_vnd": n.total_discount_vnd,
        "buyer_paid_vnd": n.buyer_paid_vnd,
        "seller_receives_vnd": n.seller_receives_vnd,
        "tracking_number": n.tracking_number,
        "estimated_delivery_date": n.estimated_delivery_date,
        "buyer_province": n.buyer_province,
        "seller_province": n.seller_province,
        "is_cross_province": n.is_cross_province,
        "platform_commission_vnd": n.platform_commission_vnd,
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


def raw_order_from_dict(d: object) -> RawOrder:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")
    return RawOrder(
        platform=Platform(_req_str(d, "platform")),
        platform_order_id=_req_str(d, "platform_order_id"),
        raw_status=_req_str(d, "raw_status"),
        raw_payment=_req_str(d, "raw_payment"),
        raw_shipping=_req_str(d, "raw_shipping"),
        item_total_vnd=_req_int(d, "item_total_vnd"),
        shipping_fee_vnd=_req_int(d, "shipping_fee_vnd"),
        platform_discount_vnd=_req_int(d, "platform_discount_vnd"),
        seller_discount_vnd=_req_int(d, "seller_discount_vnd"),
        buyer_paid_vnd=_req_int(d, "buyer_paid_vnd"),
        seller_receives_vnd=_req_int(d, "seller_receives_vnd"),
        tracking_number=_req_str(d, "tracking_number"),
        estimated_delivery_date=_req_str(d, "estimated_delivery_date"),
        buyer_province=_req_str(d, "buyer_province"),
        seller_province=_req_str(d, "seller_province"),
    )


def dump_raw(orders: list[RawOrder]) -> str:
    lines = [json.dumps(raw_order_to_dict(o), ensure_ascii=False) for o in orders]
    return "\n".join(lines) + ("\n" if lines else "")


def dump_normalised(orders: list[NormalisedOrder]) -> str:
    lines = [json.dumps(normalised_order_to_dict(o), ensure_ascii=False) for o in orders]
    return "\n".join(lines) + ("\n" if lines else "")


def load_and_normalise(text: str) -> list[NormalisedOrder]:
    out: list[NormalisedOrder] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        out.append(normalise(raw_order_from_dict(raw)))
    return out
