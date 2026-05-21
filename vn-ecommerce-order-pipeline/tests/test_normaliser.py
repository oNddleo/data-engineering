"""Tests for VN e-commerce order normaliser."""

from __future__ import annotations

import pytest

from vnecommerce.normaliser import normalise
from vnecommerce.schema import (
    OrderStatus,
    PaymentMethod,
    Platform,
    RawOrder,
    ShippingMethod,
)


def _make_raw(
    platform: Platform = Platform.SHOPEE,
    raw_status: str = "SHIPPED",
    raw_payment: str = "cod",
    raw_shipping: str = "spx_express",
    item_total: int = 500_000,
    buyer_province: str = "Hồ Chí Minh",
    seller_province: str = "Hà Nội",
) -> RawOrder:
    return RawOrder(
        platform=platform,
        platform_order_id="ORD-001",
        raw_status=raw_status,
        raw_payment=raw_payment,
        raw_shipping=raw_shipping,
        item_total_vnd=item_total,
        shipping_fee_vnd=25_000,
        platform_discount_vnd=20_000,
        seller_discount_vnd=10_000,
        buyer_paid_vnd=item_total + 25_000 - 20_000 - 10_000,
        seller_receives_vnd=int(item_total * 0.93),
        tracking_number="VN123456789",
        estimated_delivery_date="2025-06-01",
        buyer_province=buyer_province,
        seller_province=seller_province,
    )


class TestStatusMapping:
    def test_shopee_shipped(self) -> None:
        raw = _make_raw(platform=Platform.SHOPEE, raw_status="SHIPPED")
        n = normalise(raw)
        assert n.status == OrderStatus.SHIPPED

    def test_shopee_completed(self) -> None:
        raw = _make_raw(platform=Platform.SHOPEE, raw_status="COMPLETED")
        n = normalise(raw)
        assert n.status == OrderStatus.DELIVERED

    def test_shopee_cancelled(self) -> None:
        raw = _make_raw(platform=Platform.SHOPEE, raw_status="CANCELLED")
        n = normalise(raw)
        assert n.status == OrderStatus.CANCELLED

    def test_tiki_successful(self) -> None:
        raw = _make_raw(
            platform=Platform.TIKI,
            raw_status="successful",
            raw_shipping="tiki_delivery",
        )
        n = normalise(raw)
        assert n.status == OrderStatus.DELIVERED

    def test_tiki_shipping(self) -> None:
        raw = _make_raw(
            platform=Platform.TIKI, raw_status="shipping", raw_shipping="tiki_delivery"
        )
        n = normalise(raw)
        assert n.status == OrderStatus.SHIPPED

    def test_lazada_delivered(self) -> None:
        raw = _make_raw(
            platform=Platform.LAZADA,
            raw_status="delivered",
            raw_shipping="lazada_express",
        )
        n = normalise(raw)
        assert n.status == OrderStatus.DELIVERED

    def test_unknown_status_defaults_pending(self) -> None:
        raw = _make_raw(raw_status="MYSTERY_STATUS")
        n = normalise(raw)
        assert n.status == OrderStatus.PENDING


class TestPaymentMapping:
    def test_cod(self) -> None:
        raw = _make_raw(raw_payment="cod")
        assert normalise(raw).payment_method == PaymentMethod.COD

    def test_shopee_pay(self) -> None:
        raw = _make_raw(raw_payment="shopeepay")
        assert normalise(raw).payment_method == PaymentMethod.SHOPEE_PAY

    def test_tiki_wallet(self) -> None:
        raw = _make_raw(raw_payment="tiki_wallet")
        assert normalise(raw).payment_method == PaymentMethod.TIKI_WALLET

    def test_momo(self) -> None:
        raw = _make_raw(raw_payment="momo")
        assert normalise(raw).payment_method == PaymentMethod.MOMO

    def test_installment(self) -> None:
        raw = _make_raw(raw_payment="installment")
        assert normalise(raw).payment_method == PaymentMethod.INSTALLMENT

    def test_unknown_payment_defaults_cod(self) -> None:
        raw = _make_raw(raw_payment="unknown_method")
        assert normalise(raw).payment_method == PaymentMethod.COD


class TestShippingMapping:
    def test_spx_express(self) -> None:
        raw = _make_raw(raw_shipping="spx_express")
        assert normalise(raw).shipping_method == ShippingMethod.EXPRESS

    def test_spx_economy(self) -> None:
        raw = _make_raw(raw_shipping="spx_economy")
        assert normalise(raw).shipping_method == ShippingMethod.ECONOMY

    def test_same_day(self) -> None:
        raw = _make_raw(raw_shipping="now")
        assert normalise(raw).shipping_method == ShippingMethod.SAME_DAY

    def test_tiki_fast_delivery(self) -> None:
        raw = _make_raw(raw_shipping="fast_delivery")
        assert normalise(raw).shipping_method == ShippingMethod.EXPRESS

    def test_unknown_shipping_defaults_standard(self) -> None:
        raw = _make_raw(raw_shipping="mystery_carrier")
        assert normalise(raw).shipping_method == ShippingMethod.STANDARD


class TestAmounts:
    def test_total_discount(self) -> None:
        raw2 = RawOrder(
            platform=Platform.SHOPEE,
            platform_order_id="ORD-002",
            raw_status="SHIPPED",
            raw_payment="cod",
            raw_shipping="spx_express",
            item_total_vnd=1_000_000,
            shipping_fee_vnd=0,
            platform_discount_vnd=50_000,
            seller_discount_vnd=30_000,
            buyer_paid_vnd=920_000,
            seller_receives_vnd=880_000,
            tracking_number="VN000",
            estimated_delivery_date="",
            buyer_province="HCM",
            seller_province="HN",
        )
        n = normalise(raw2)
        assert n.total_discount_vnd == 80_000

    def test_cross_province(self) -> None:
        raw = _make_raw(buyer_province="Hồ Chí Minh", seller_province="Hà Nội")
        assert normalise(raw).is_cross_province is True

    def test_same_province(self) -> None:
        raw = _make_raw(buyer_province="Hồ Chí Minh", seller_province="Hồ Chí Minh")
        assert normalise(raw).is_cross_province is False


class TestValidation:
    def test_empty_order_id_raises(self) -> None:
        with pytest.raises(ValueError):
            RawOrder(
                platform=Platform.SHOPEE,
                platform_order_id="",
                raw_status="SHIPPED",
                raw_payment="cod",
                raw_shipping="spx_express",
                item_total_vnd=100_000,
                shipping_fee_vnd=0,
                platform_discount_vnd=0,
                seller_discount_vnd=0,
                buyer_paid_vnd=100_000,
                seller_receives_vnd=90_000,
                tracking_number="VN000",
                estimated_delivery_date="",
                buyer_province="HCM",
                seller_province="HCM",
            )

    def test_negative_item_total_raises(self) -> None:
        with pytest.raises(ValueError):
            _make_raw(item_total=-1)
