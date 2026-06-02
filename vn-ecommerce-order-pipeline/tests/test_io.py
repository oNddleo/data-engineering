"""JSONL I/O tests for VN e-commerce order pipeline."""

from __future__ import annotations

from vnecommerce.io_jsonl import dump_normalised, dump_raw, load_and_normalise
from vnecommerce.normaliser import normalise
from vnecommerce.schema import Platform, RawOrder


def _sample_raw(order_id: str = "ORD-001", platform: Platform = Platform.SHOPEE) -> RawOrder:
    return RawOrder(
        platform=platform,
        platform_order_id=order_id,
        raw_status="SHIPPED",
        raw_payment="cod",
        raw_shipping="spx_express",
        item_total_vnd=500_000,
        shipping_fee_vnd=25_000,
        platform_discount_vnd=10_000,
        seller_discount_vnd=5_000,
        buyer_paid_vnd=510_000,
        seller_receives_vnd=465_000,
        tracking_number="VN123",
        estimated_delivery_date="2025-06-01",
        buyer_province="Hồ Chí Minh",
        seller_province="Hà Nội",
    )


def test_dump_raw_is_jsonl() -> None:
    import json

    orders = [_sample_raw("A"), _sample_raw("B")]
    text = dump_raw(orders)
    lines = [ln for ln in text.strip().splitlines() if ln]
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "platform" in obj
        assert "item_total_vnd" in obj


def test_dump_normalised_is_jsonl() -> None:
    import json

    orders = [normalise(_sample_raw())]
    text = dump_normalised(orders)
    obj = json.loads(text.strip())
    assert obj["status"] == "SHIPPED"
    assert obj["payment_method"] == "COD"


def test_load_and_normalise_roundtrip() -> None:
    # Use tiki status and shipping
    raw2 = RawOrder(
        platform=Platform.TIKI,
        platform_order_id="X",
        raw_status="shipping",
        raw_payment="cod",
        raw_shipping="tiki_delivery",
        item_total_vnd=300_000,
        shipping_fee_vnd=0,
        platform_discount_vnd=0,
        seller_discount_vnd=0,
        buyer_paid_vnd=300_000,
        seller_receives_vnd=270_000,
        tracking_number="VN999",
        estimated_delivery_date="",
        buyer_province="Hà Nội",
        seller_province="Hà Nội",
    )
    text = dump_raw([raw2])
    loaded = load_and_normalise(text)
    assert len(loaded) == 1
    from vnecommerce.schema import OrderStatus

    assert loaded[0].status == OrderStatus.SHIPPED


def test_dump_normalised_empty() -> None:
    assert dump_normalised([]) == ""


def test_load_empty_text() -> None:
    assert load_and_normalise("") == []
