"""SKU registry — link platform item ids to canonical SKUs.

In practice this table is curated upstream: an analyst tags
"Shopee item 12345 = Lazada item ABC = Tiki item 999 = same iPhone
14 Pro 256GB" via barcode lookup or product-matching ML. The
``SkuRegistry`` here is just the storage + lookup surface.

Lookups go both ways: given a canonical SKU you can find every
``(platform, platform_item_id)`` it lives at; given a
``(platform, platform_item_id)`` you can find its canonical SKU.

Insertion rejects duplicates — registering the same
``(platform, item_id)`` twice with different canonical SKUs is
almost always a bug in the upstream tagger.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from multiprice.schema import Platform, SkuMapping


class SkuRegistry:
    """Bidirectional mapping between canonical SKUs and platform item ids."""

    def __init__(self) -> None:
        self._platform_to_sku: dict[tuple[Platform, str], str] = {}
        self._sku_to_platforms: dict[str, dict[Platform, str]] = {}

    def __len__(self) -> int:
        return len(self._platform_to_sku)

    @property
    def n_skus(self) -> int:
        return len(self._sku_to_platforms)

    def register(self, mapping: SkuMapping) -> None:
        key = (mapping.platform, mapping.platform_item_id)
        existing = self._platform_to_sku.get(key)
        if existing is not None and existing != mapping.canonical_sku:
            raise ValueError(
                f"{mapping.platform.value}:{mapping.platform_item_id} already "
                f"registered to SKU {existing!r}, cannot remap to "
                f"{mapping.canonical_sku!r}"
            )
        self._platform_to_sku[key] = mapping.canonical_sku
        per_sku = self._sku_to_platforms.setdefault(mapping.canonical_sku, {})
        per_sku[mapping.platform] = mapping.platform_item_id

    def register_many(self, mappings: Iterable[SkuMapping]) -> None:
        for m in mappings:
            self.register(m)

    def canonical_sku(self, platform: Platform, platform_item_id: str) -> str | None:
        return self._platform_to_sku.get((platform, platform_item_id))

    def platforms_for(self, canonical_sku: str) -> dict[Platform, str]:
        return dict(self._sku_to_platforms.get(canonical_sku, {}))

    def all_skus(self) -> set[str]:
        return set(self._sku_to_platforms)


__all__ = ["SkuRegistry"]
