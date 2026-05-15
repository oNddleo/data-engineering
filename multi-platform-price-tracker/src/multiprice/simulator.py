"""Seeded synthetic multi-platform price data."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from multiprice.schema import VN_TZ, Platform, ProductObservation, SkuMapping

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


_PRODUCT_NAMES = (
    "iPhone 14 Pro 256GB",
    "Samsung Galaxy S24 Ultra",
    "Áo thun Uniqlo Nam",
    "Tủ lạnh Samsung Inverter 322L",
    "Máy lọc nước Karofi K8",
    "Bia Heineken 24 lon",
    "Cà phê G7 hộp 100 gói",
    "Nồi cơm điện Cuckoo CR-0631",
    "Tai nghe Sony WH-1000XM5",
    "Laptop Dell XPS 13 i7",
    "Sữa bột Vinamilk Optimum 800g",
    "Mì gói Hảo Hảo thùng 30 gói",
)


def _platform_item_id(rng: random.Random, platform: Platform, idx: int) -> str:
    if platform is Platform.SHOPEE:
        return f"sp-{idx:08d}"
    if platform is Platform.LAZADA:
        return f"lz-{idx:08d}-{rng.randint(100, 999)}"
    return f"tk-{1_000_000 + idx}"


def generate(
    *,
    n_skus: int = 12,
    n_snapshots: int = 5,
    snapshot_interval_hours: int = 6,
    seed: int = 0,
    base_time: datetime | None = None,
    arbitrage_skus: int = 0,
    stockout_skus: int = 0,
) -> tuple[list[SkuMapping], list[ProductObservation]]:
    """Produce ``(mappings, observations)`` covering ``n_skus`` SKUs across
    Shopee, Lazada, and Tiki, with ``n_snapshots`` price points per
    ``(sku, platform)`` series.

    ``arbitrage_skus`` SKUs get a 25 % price wedge between platforms;
    ``stockout_skus`` SKUs have ``stock = 0`` on the latest snapshot
    for one randomly-chosen platform.
    """
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    mappings: list[SkuMapping] = []
    observations: list[ProductObservation] = []

    for i in range(n_skus):
        sku = f"SKU-{8_000_000_000 + i}"
        name = rng.choice(_PRODUCT_NAMES)
        # Base price for this SKU across all platforms.
        base_price = rng.choice(
            [99_000, 199_000, 499_000, 999_000, 4_999_000, 9_999_000, 19_999_000]
        )
        is_arbitrage = i < arbitrage_skus
        is_stockout = i < stockout_skus

        for plat in Platform:
            item_id = _platform_item_id(rng, plat, i)
            mappings.append(SkuMapping(canonical_sku=sku, platform=plat, platform_item_id=item_id))
            # Per-platform price baseline: small ±5 % jitter from the SKU base.
            platform_price = int(base_price * (1 + rng.uniform(-0.05, 0.05)))
            # Optional arbitrage wedge: one platform gets +25 %.
            if is_arbitrage and plat is Platform.LAZADA:
                platform_price = int(platform_price * 1.25)
            current_price = platform_price
            for s in range(n_snapshots):
                t = base + timedelta(hours=snapshot_interval_hours * s)
                # Each snapshot may drop the price slightly.
                if s > 0:
                    current_price = max(int(current_price * rng.uniform(0.95, 1.0)), 1_000)
                stock = rng.randint(0, 200)
                if is_stockout and s == n_snapshots - 1 and plat is Platform.SHOPEE:
                    stock = 0
                observations.append(
                    ProductObservation(
                        canonical_sku=sku,
                        platform=plat,
                        platform_item_id=item_id,
                        name=name,
                        price_vnd=current_price,
                        original_price_vnd=platform_price,  # original = first snapshot's price
                        stock=stock,
                        observed_at=t,
                    )
                )
    observations.sort(key=lambda o: (o.canonical_sku, o.platform.value, o.observed_at))
    return mappings, observations


__all__ = ["generate"]
