"""Core domain types for VN e-commerce order pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Platform(str, Enum):
    """Vietnam e-commerce platforms."""

    SHOPEE = "SHOPEE"
    TIKI = "TIKI"
    LAZADA = "LAZADA"
    TIKINGNON = "TIKINGNON"  # TikiNgon (fresh/grocery)
    SENDO = "SENDO"


class OrderStatus(str, Enum):
    """Normalised order lifecycle status."""

    PENDING = "PENDING"  # awaiting confirmation
    CONFIRMED = "CONFIRMED"  # seller confirmed
    PICKING = "PICKING"  # warehouse picking
    SHIPPED = "SHIPPED"  # in transit
    DELIVERED = "DELIVERED"  # delivered to buyer
    CANCELLED = "CANCELLED"  # cancelled (any party)
    RETURNING = "RETURNING"  # return in progress
    REFUNDED = "REFUNDED"  # money returned


class PaymentMethod(str, Enum):
    """Payment method normalised across platforms."""

    COD = "COD"  # Cash on Delivery
    VNPAY = "VNPAY"
    MOMO = "MOMO"
    ZALOPAY = "ZALOPAY"
    BANK_TRANSFER = "BANK_TRANSFER"
    SHOPEE_PAY = "SHOPEE_PAY"
    TIKI_WALLET = "TIKI_WALLET"
    CREDIT_CARD = "CREDIT_CARD"
    INSTALLMENT = "INSTALLMENT"  # trả góp


class ShippingMethod(str, Enum):
    """Shipping method normalised across platforms."""

    EXPRESS = "EXPRESS"  # next-day
    STANDARD = "STANDARD"  # 2-5 days
    ECONOMY = "ECONOMY"  # 5-10 days
    SAME_DAY = "SAME_DAY"  # within hours (metro areas)
    BULKY = "BULKY"  # large items
    PICKUP = "PICKUP"  # buyer picks up


@dataclass(frozen=True, slots=True)
class RawOrder:
    """Platform-specific raw order before normalisation."""

    platform: Platform
    platform_order_id: str  # e.g. "250521XXXXXX" (Shopee)
    raw_status: str  # platform-specific status string
    raw_payment: str  # platform-specific payment string
    raw_shipping: str  # platform-specific shipping string
    # Amounts in VND (platforms report in VND by regulation)
    item_total_vnd: int  # sum of item prices × quantities
    shipping_fee_vnd: int  # buyer-paid shipping
    platform_discount_vnd: int  # platform voucher deduction
    seller_discount_vnd: int  # seller voucher deduction
    buyer_paid_vnd: int  # actual amount charged to buyer
    seller_receives_vnd: int  # after platform commission
    # Logistics
    tracking_number: str
    estimated_delivery_date: str  # ISO 8601 date string or ""
    # Address
    buyer_province: str  # e.g. "Hồ Chí Minh"
    seller_province: str

    def __post_init__(self) -> None:
        if not self.platform_order_id:
            raise ValueError("platform_order_id cannot be empty")
        if self.item_total_vnd < 0:
            raise ValueError("item_total_vnd must be >= 0")
        if self.shipping_fee_vnd < 0:
            raise ValueError("shipping_fee_vnd must be >= 0")
        if self.buyer_paid_vnd < 0:
            raise ValueError("buyer_paid_vnd must be >= 0")
