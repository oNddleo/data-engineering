"""Order normalisation logic: map platform-specific fields to canonical schema."""

from __future__ import annotations

from dataclasses import dataclass

from vnecommerce.schema import (
    OrderStatus,
    PaymentMethod,
    Platform,
    RawOrder,
    ShippingMethod,
)

# ---- Status mappings per platform -----------------------------------------------

_SHOPEE_STATUS: dict[str, OrderStatus] = {
    "UNPAID": OrderStatus.PENDING,
    "READY_TO_SHIP": OrderStatus.CONFIRMED,
    "PROCESSED": OrderStatus.PICKING,
    "SHIPPED": OrderStatus.SHIPPED,
    "IN_CANCEL": OrderStatus.CANCELLED,
    "CANCELLED": OrderStatus.CANCELLED,
    "COMPLETED": OrderStatus.DELIVERED,
    "TO_RETURN": OrderStatus.RETURNING,
    "REFUND": OrderStatus.REFUNDED,
}

_TIKI_STATUS: dict[str, OrderStatus] = {
    "queued": OrderStatus.PENDING,
    "processing": OrderStatus.CONFIRMED,
    "picking": OrderStatus.PICKING,
    "shipping": OrderStatus.SHIPPED,
    "successful": OrderStatus.DELIVERED,
    "canceled": OrderStatus.CANCELLED,
    "returning": OrderStatus.RETURNING,
    "returned": OrderStatus.REFUNDED,
}

_LAZADA_STATUS: dict[str, OrderStatus] = {
    "pending": OrderStatus.PENDING,
    "packed": OrderStatus.PICKING,
    "ready_to_ship_pending": OrderStatus.CONFIRMED,
    "shipped": OrderStatus.SHIPPED,
    "delivered": OrderStatus.DELIVERED,
    "canceled": OrderStatus.CANCELLED,
    "returned": OrderStatus.RETURNING,
}

_STATUS_MAP: dict[Platform, dict[str, OrderStatus]] = {
    Platform.SHOPEE: _SHOPEE_STATUS,
    Platform.TIKI: _TIKI_STATUS,
    Platform.TIKINGNON: _TIKI_STATUS,
    Platform.LAZADA: _LAZADA_STATUS,
    Platform.SENDO: {},
}

# ---- Payment method mappings -------------------------------------------------------

_PAYMENT_MAP: dict[str, PaymentMethod] = {
    # Shopee
    "cod": PaymentMethod.COD,
    "cash_on_delivery": PaymentMethod.COD,
    "shopeepay": PaymentMethod.SHOPEE_PAY,
    "shopee_pay": PaymentMethod.SHOPEE_PAY,
    "credit_card": PaymentMethod.CREDIT_CARD,
    "vnpay": PaymentMethod.VNPAY,
    "momo": PaymentMethod.MOMO,
    "zalopay": PaymentMethod.ZALOPAY,
    "bank_transfer": PaymentMethod.BANK_TRANSFER,
    # Tiki
    "tiki_wallet": PaymentMethod.TIKI_WALLET,
    "tikiwallet": PaymentMethod.TIKI_WALLET,
    "installment": PaymentMethod.INSTALLMENT,
    "tra_gop": PaymentMethod.INSTALLMENT,
    # Lazada
    "hellopay": PaymentMethod.BANK_TRANSFER,
    "lazadawallet": PaymentMethod.BANK_TRANSFER,
}

# ---- Shipping method mappings ------------------------------------------------------

_SHIPPING_MAP: dict[str, ShippingMethod] = {
    # Shopee
    "spx_express": ShippingMethod.EXPRESS,
    "spx_standard": ShippingMethod.STANDARD,
    "spx_economy": ShippingMethod.ECONOMY,
    "now": ShippingMethod.SAME_DAY,
    "shopee_express": ShippingMethod.EXPRESS,
    # Tiki
    "tikingon_delivery": ShippingMethod.SAME_DAY,
    "tiki_delivery": ShippingMethod.EXPRESS,
    "cross_border": ShippingMethod.ECONOMY,
    "fast_delivery": ShippingMethod.EXPRESS,
    "standard_delivery": ShippingMethod.STANDARD,
    # Lazada
    "lazada_express": ShippingMethod.EXPRESS,
    "lazada_standard": ShippingMethod.STANDARD,
    "bulky_item": ShippingMethod.BULKY,
    "lex": ShippingMethod.EXPRESS,
}


def _map_status(platform: Platform, raw: str) -> OrderStatus:
    table = _STATUS_MAP.get(platform, {})
    return table.get(raw.lower(), table.get(raw, OrderStatus.PENDING))


def _map_payment(raw: str) -> PaymentMethod:
    return _PAYMENT_MAP.get(raw.lower(), PaymentMethod.COD)


def _map_shipping(raw: str) -> ShippingMethod:
    return _SHIPPING_MAP.get(raw.lower(), ShippingMethod.STANDARD)


def _effective_discount(raw: RawOrder) -> int:
    return raw.platform_discount_vnd + raw.seller_discount_vnd


def _is_cross_province(raw: RawOrder) -> bool:
    """True if buyer and seller are in different provinces."""
    return raw.buyer_province.strip() != raw.seller_province.strip()


@dataclass(frozen=True, slots=True)
class NormalisedOrder:
    """Platform-agnostic normalised order record."""

    platform: Platform
    platform_order_id: str
    status: OrderStatus
    payment_method: PaymentMethod
    shipping_method: ShippingMethod
    item_total_vnd: int
    shipping_fee_vnd: int
    total_discount_vnd: int
    buyer_paid_vnd: int
    seller_receives_vnd: int
    tracking_number: str
    estimated_delivery_date: str
    buyer_province: str
    seller_province: str
    is_cross_province: bool
    # Derived fields
    platform_commission_vnd: int  # item_total - discount - seller_receives (approx)


def normalise(raw: RawOrder) -> NormalisedOrder:
    """Normalise a platform-specific raw order to canonical form."""
    total_discount = _effective_discount(raw)
    # Approximate platform commission = what buyer paid - shipping - what seller gets
    # (rough: actual calculation includes platform-specific fee structures)
    commission = max(0, raw.buyer_paid_vnd - raw.shipping_fee_vnd - raw.seller_receives_vnd)

    return NormalisedOrder(
        platform=raw.platform,
        platform_order_id=raw.platform_order_id,
        status=_map_status(raw.platform, raw.raw_status),
        payment_method=_map_payment(raw.raw_payment),
        shipping_method=_map_shipping(raw.raw_shipping),
        item_total_vnd=raw.item_total_vnd,
        shipping_fee_vnd=raw.shipping_fee_vnd,
        total_discount_vnd=total_discount,
        buyer_paid_vnd=raw.buyer_paid_vnd,
        seller_receives_vnd=raw.seller_receives_vnd,
        tracking_number=raw.tracking_number,
        estimated_delivery_date=raw.estimated_delivery_date,
        buyer_province=raw.buyer_province,
        seller_province=raw.seller_province,
        is_cross_province=_is_cross_province(raw),
        platform_commission_vnd=commission,
    )
