"""Seeded synthetic dimension snapshots.

Generates a pair of snapshots (``before``, ``after``) that exercises
all three change kinds: INSERT, UPDATE, DELETE. The simulator is
modelled on a Shopee seller dimension with realistic attribute churn:
shop name renames, address updates, tier promotions, occasional
deletions.
"""

from __future__ import annotations

import random

# Bundled attribute generators for a "seller" dimension.
_SHOP_NAME_PREFIXES = (
    "Shop",
    "Cua hang",
    "Quan",
    "Tiem",
    "Boutique",
    "Mart",
    "Store",
)
_SHOP_NAME_SUFFIXES = (
    "Sai Gon",
    "Hà Nội",
    "Đà Nẵng",
    "Cần Thơ",
    "Hải Phòng",
    "Huế",
    "Nha Trang",
    "Quy Nhơn",
)
_TIERS = ("BASIC", "STANDARD", "PREFERRED", "MALL")
_REGIONS = ("HCMC", "HN", "DN", "CT", "HP", "NT", "QN", "BD")


def _shop_name(rng: random.Random) -> str:
    return f"{rng.choice(_SHOP_NAME_PREFIXES)} {rng.choice(_SHOP_NAME_SUFFIXES)}"


def _make_attrs(rng: random.Random) -> dict[str, str]:
    return {
        "shop_name": _shop_name(rng),
        "tier": rng.choice(_TIERS),
        "region": rng.choice(_REGIONS),
        "is_verified": "true" if rng.random() < 0.6 else "false",
    }


def generate_pair(
    *,
    n_entities: int = 50,
    insert_fraction: float = 0.10,
    delete_fraction: float = 0.05,
    update_fraction: float = 0.30,
    seed: int = 0,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Generate ``(before, after)`` snapshots with realistic churn.

    ``before`` has ``n_entities`` rows. ``after`` keeps all but
    ``delete_fraction`` × n, mutates ``update_fraction`` × n, and adds
    ``insert_fraction`` × n new entities.
    """
    if n_entities < 1:
        raise ValueError("n_entities must be >= 1")
    for name, val in (
        ("insert_fraction", insert_fraction),
        ("delete_fraction", delete_fraction),
        ("update_fraction", update_fraction),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    rng = random.Random(seed)

    before: dict[str, dict[str, str]] = {}
    for i in range(n_entities):
        before[f"S-{i:06d}"] = _make_attrs(rng)

    after: dict[str, dict[str, str]] = {}
    keys = list(before)
    rng.shuffle(keys)
    n_delete = int(n_entities * delete_fraction)
    n_update = int(n_entities * update_fraction)

    # Carry over kept keys with possible mutations.
    for i, k in enumerate(keys[n_delete:]):
        attrs = dict(before[k])
        if i < n_update:
            # Mutate one or two random attributes.
            for attr_name in rng.sample(list(attrs), rng.randint(1, 2)):
                if attr_name == "shop_name":
                    attrs[attr_name] = _shop_name(rng)
                elif attr_name == "tier":
                    attrs[attr_name] = rng.choice(_TIERS)
                elif attr_name == "region":
                    attrs[attr_name] = rng.choice(_REGIONS)
                elif attr_name == "is_verified":
                    attrs[attr_name] = "true" if attrs[attr_name] == "false" else "false"
        after[k] = attrs

    # Add inserts.
    n_insert = int(n_entities * insert_fraction)
    for j in range(n_insert):
        new_id = f"S-{n_entities + j:06d}"
        after[new_id] = _make_attrs(rng)

    return before, after


__all__ = ["generate_pair"]
