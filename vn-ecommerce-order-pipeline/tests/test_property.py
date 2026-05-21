"""Property-based tests for VN e-commerce normaliser."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnecommerce.normaliser import normalise
from vnecommerce.schema import OrderStatus, Platform, RawOrder


def _make_valid_raw(
    platform: str,
    raw_status: str,
    item_total: int,
    shipping: int,
    disc: int,
    buyer_prov: str,
    seller_prov: str,
) -> RawOrder:
    buyer_paid = max(0, item_total + shipping - disc)
    seller_rec = max(0, int(item_total * 0.9))
    return RawOrder(
        platform=Platform(platform),
        platform_order_id="ORD-1",
        raw_status=raw_status,
        raw_payment="cod",
        raw_shipping="spx_express",
        item_total_vnd=item_total,
        shipping_fee_vnd=shipping,
        platform_discount_vnd=disc,
        seller_discount_vnd=0,
        buyer_paid_vnd=buyer_paid,
        seller_receives_vnd=seller_rec,
        tracking_number="VN1",
        estimated_delivery_date="",
        buyer_province=buyer_prov,
        seller_province=seller_prov,
    )


@given(
    item_total=st.integers(min_value=1, max_value=10_000_000),
    shipping=st.integers(min_value=0, max_value=200_000),
    disc=st.integers(min_value=0, max_value=500_000),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_normalise_never_raises_for_valid_amounts(
    item_total: int, shipping: int, disc: int
) -> None:
    raw = _make_valid_raw("SHOPEE", "SHIPPED", item_total, shipping, disc, "HCM", "HN")
    n = normalise(raw)
    assert n.buyer_paid_vnd >= 0
    assert n.seller_receives_vnd >= 0
    assert n.total_discount_vnd >= 0


@given(
    platform=st.sampled_from(["SHOPEE", "TIKI", "LAZADA"]),
    raw_status=st.text(min_size=1, max_size=30),
)
@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_unknown_status_maps_to_valid_status(platform: str, raw_status: str) -> None:
    """Unknown status strings should produce a valid OrderStatus (no crash)."""
    raw = _make_valid_raw(platform, raw_status, 100_000, 0, 0, "HCM", "HCM")
    n = normalise(raw)
    assert isinstance(n.status, OrderStatus)


@given(
    buyer_prov=st.text(min_size=1, max_size=50),
    seller_prov=st.text(min_size=1, max_size=50),
)
@settings(max_examples=30)
def test_cross_province_detection(buyer_prov: str, seller_prov: str) -> None:
    raw = _make_valid_raw("SHOPEE", "SHIPPED", 100_000, 0, 0, buyer_prov, seller_prov)
    n = normalise(raw)
    assert n.is_cross_province == (buyer_prov.strip() != seller_prov.strip())


@given(st.integers(min_value=0, max_value=5_000_000))
@settings(max_examples=30)
def test_commission_never_negative(item_total: int) -> None:
    raw = _make_valid_raw("SHOPEE", "COMPLETED", item_total, 0, 0, "HCM", "HN")
    n = normalise(raw)
    assert n.platform_commission_vnd >= 0
