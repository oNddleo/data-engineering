"""The three canonical reservoir-sampling algorithms.

* **Algorithm R** (Vitter 1985) — the textbook approach. For each
  arriving item at position ``i`` (1-indexed):

    - If ``i ≤ k``: store it in slot ``i − 1``.
    - Else: pick ``j`` uniformly from ``[0, i)``; if ``j < k`` replace
      slot ``j`` with the new item.

  Cost: O(N) — one random draw per stream item.

* **Algorithm L** (Li 1994) — equivalent uniform sample but uses
  *geometric jumps* to skip past items that wouldn't change the
  reservoir, reducing the expected RNG calls to
  ``O(k · (1 + log(N/k)))``. Faster for large N.

* **A-Res** (Efraimidis & Spirakis 2006) — weighted reservoir. Each
  item ``v_i`` with weight ``w_i > 0`` is assigned a key
  ``key_i = u_i^(1/w_i)`` where ``u_i ∼ U(0, 1)``. Keep the top-k
  largest keys. Probability of ending in the sample is monotone in
  weight (matches the **weighted-without-replacement** scheme).

All three accept any iterable of strings and respect a caller-
supplied ``random.Random`` for determinism.
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from reservoir.schema import (
    BuildableReservoir,
    Reservoir,
    WeightedItem,
    WeightedReservoir,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


# ---------- Algorithm R (Vitter 1985) ---------------------------------------


def build_r(capacity: int) -> BuildableReservoir:
    """Construct an empty reservoir sized for Algorithm R."""
    if capacity < 1:
        raise ValueError(f"capacity must be >= 1, got {capacity}")
    return BuildableReservoir(capacity=capacity)


def add_r(
    res: BuildableReservoir,
    value: str,
    *,
    rng: random.Random | None = None,
) -> None:
    """Feed one stream item to a reservoir using Algorithm R."""
    r = rng if rng is not None else random.Random()
    res.n_seen += 1
    if len(res.items) < res.capacity:
        res.items.append(value)
        return
    # 0-indexed slot to replace, drawn uniformly from [0, n_seen).
    j = r.randrange(res.n_seen)
    if j < res.capacity:
        res.items[j] = value


def sample_r(
    stream: Iterable[str],
    capacity: int,
    *,
    rng: random.Random | None = None,
) -> Reservoir:
    """One-shot helper: drain ``stream`` into a fresh reservoir with Algorithm R."""
    res = build_r(capacity)
    for v in stream:
        add_r(res, v, rng=rng)
    return freeze(res)


# ---------- Algorithm L (Li 1994) ------------------------------------------


def build_l(
    capacity: int,
    *,
    rng: random.Random | None = None,
) -> BuildableReservoir:
    """Construct an empty reservoir for Algorithm L.

    The skip state (``_w``, ``_next_index``) is initialised the first
    time the reservoir fills up — see ``add_l``.
    """
    if capacity < 1:
        raise ValueError(f"capacity must be >= 1, got {capacity}")
    return BuildableReservoir(capacity=capacity)


def add_l(
    res: BuildableReservoir,
    value: str,
    *,
    rng: random.Random | None = None,
) -> None:
    """Feed one stream item to a reservoir using Algorithm L.

    Fill phase (n_seen ≤ k): identical to Algorithm R.
    Steady phase (n_seen > k): only act when ``n_seen == _next_index``;
    otherwise skip cheaply.
    """
    r = rng if rng is not None else random.Random()
    res.n_seen += 1
    if len(res.items) < res.capacity:
        res.items.append(value)
        # First fill done — initialise skip state for the steady phase.
        # Next item to consider is k + 1 + geometric_jump (Li 1994 §3).
        if len(res.items) == res.capacity:
            res._w = math.exp(math.log(r.random()) / res.capacity)
            res._next_index = res.capacity + 1 + _geometric_jump(res._w, r)
        return
    if res.n_seen == res._next_index:
        j = r.randrange(res.capacity)
        res.items[j] = value
        # Advance the skip cursor.
        res._w *= math.exp(math.log(r.random()) / res.capacity)
        res._next_index += 1 + _geometric_jump(res._w, r)


def sample_l(
    stream: Iterable[str],
    capacity: int,
    *,
    rng: random.Random | None = None,
) -> Reservoir:
    """One-shot helper: drain ``stream`` into a fresh reservoir with Algorithm L."""
    r = rng if rng is not None else random.Random()
    res = build_l(capacity, rng=r)
    for v in stream:
        add_l(res, v, rng=r)
    return freeze(res)


def _geometric_jump(w: float, rng: random.Random) -> int:
    """Return ``floor(log(u) / log(1 - w))`` — the L-paper skip length."""
    u = rng.random()
    # Guard the degenerate case w ≥ 1 (shouldn't happen but avoid log(0)).
    denom = math.log(1.0 - w) if w < 1.0 else -1e-9
    return int(math.floor(math.log(u) / denom))


# ---------- A-Res weighted (Efraimidis–Spirakis 2006) ----------------------


def build_weighted(capacity: int) -> WeightedReservoir:
    """Construct an empty weighted reservoir for A-Res."""
    if capacity < 1:
        raise ValueError(f"capacity must be >= 1, got {capacity}")
    return WeightedReservoir(capacity=capacity)


def add_weighted(
    res: WeightedReservoir,
    value: str,
    weight: float,
    *,
    rng: random.Random | None = None,
) -> None:
    """Feed one weighted item into the reservoir using A-Res."""
    if weight <= 0:
        raise ValueError(f"weight must be > 0, got {weight}")
    if not math.isfinite(weight):
        raise ValueError(f"weight must be finite, got {weight}")
    r = rng if rng is not None else random.Random()
    res.n_seen += 1
    res.total_weight_seen += weight
    u = r.random()
    # Guard u == 0 — extremely unlikely but produces log(0).
    if u == 0.0:
        u = 1e-12
    key = u ** (1.0 / weight)
    new_item = WeightedItem(value=value, weight=weight, key=key)

    if len(res.items) < res.capacity:
        # Insert in ascending order so items[0] always has the smallest key.
        _insert_sorted(res.items, new_item)
        return
    # Steady state: evict the smallest key if the new key beats it.
    if key > res.items[0].key:
        # Drop slot 0, insert in order.
        res.items.pop(0)
        _insert_sorted(res.items, new_item)


def sample_weighted(
    pairs: Iterable[tuple[str, float]],
    capacity: int,
    *,
    rng: random.Random | None = None,
) -> WeightedReservoir:
    """One-shot helper: drain weighted ``pairs`` into a fresh A-Res reservoir."""
    res = build_weighted(capacity)
    for value, weight in pairs:
        add_weighted(res, value, weight, rng=rng)
    return res


def _insert_sorted(items: list[WeightedItem], new_item: WeightedItem) -> None:
    """Insert ``new_item`` into ``items`` keeping the list sorted by key asc."""
    # Linear-scan insert — items is bounded by ``capacity`` (small).
    pos = 0
    while pos < len(items) and items[pos].key < new_item.key:
        pos += 1
    items.insert(pos, new_item)


# ---------- Snapshot helpers -----------------------------------------------


def freeze(res: BuildableReservoir) -> Reservoir:
    """Snapshot a mutable reservoir into an immutable ``Reservoir``."""
    return Reservoir(
        capacity=res.capacity,
        items=tuple(res.items),
        n_seen=res.n_seen,
    )


def thaw(snapshot: Reservoir) -> BuildableReservoir:
    """Rebuild a mutable reservoir from an immutable snapshot.

    The Algorithm-L skip state is reset — subsequent inserts via
    ``add_l`` will re-enter the fill phase logic for any underfilled
    slots, then re-derive ``_w`` and ``_next_index`` on first
    overflow.
    """
    return BuildableReservoir(
        capacity=snapshot.capacity,
        items=list(snapshot.items),
        n_seen=snapshot.n_seen,
    )


__all__ = [
    "add_l",
    "add_r",
    "add_weighted",
    "build_l",
    "build_r",
    "build_weighted",
    "freeze",
    "sample_l",
    "sample_r",
    "sample_weighted",
    "thaw",
]
