"""ObservationStore tests."""

from __future__ import annotations

from multiprice.schema import Platform
from multiprice.store import ObservationStore

from ._fixtures import make_obs, t_at


def test_empty_store():
    s = ObservationStore()
    assert len(s) == 0
    assert s.latest("SKU-X", Platform.SHOPEE) is None


def test_append_one():
    s = ObservationStore()
    s.append(make_obs())
    assert len(s) == 1
    assert s.n_series == 1


def test_latest_returns_most_recent():
    s = ObservationStore()
    for i in range(5):
        s.append(make_obs(price=100_000 + i * 1_000, observed_at=t_at(i * 10)))
    latest = s.latest("SKU-1", Platform.SHOPEE)
    assert latest is not None
    assert latest.price_vnd == 104_000


def test_history_returns_sorted():
    s = ObservationStore()
    s.append(make_obs(price=100, observed_at=t_at(30)))
    s.append(make_obs(price=200, observed_at=t_at(0)))
    s.append(make_obs(price=150, observed_at=t_at(15)))
    hist = s.history("SKU-1", Platform.SHOPEE)
    times = [h.observed_at for h in hist]
    assert times == sorted(times)


def test_history_window():
    s = ObservationStore()
    for i in range(5):
        s.append(make_obs(price=100_000 + i, observed_at=t_at(i * 10)))
    out = s.history("SKU-1", Platform.SHOPEE, since=t_at(15), until=t_at(35))
    assert len(out) == 2


def test_all_latest_for_sku():
    s = ObservationStore()
    s.append(make_obs(platform=Platform.SHOPEE, platform_item_id="sp", price=100))
    s.append(make_obs(platform=Platform.LAZADA, platform_item_id="lz", price=110))
    s.append(make_obs(platform=Platform.TIKI, platform_item_id="tk", price=120))
    latest = s.all_latest_for_sku("SKU-1")
    assert {p for p in latest} == {Platform.SHOPEE, Platform.LAZADA, Platform.TIKI}


def test_all_skus():
    s = ObservationStore()
    s.append(make_obs(canonical_sku="A"))
    s.append(make_obs(canonical_sku="B"))
    assert s.all_skus() == {"A", "B"}


def test_append_many():
    s = ObservationStore()
    s.append_many([make_obs(canonical_sku=f"S-{i}") for i in range(5)])
    assert len(s) == 5


def test_n_series_counts_unique_pairs():
    s = ObservationStore()
    s.append(make_obs(canonical_sku="A", platform=Platform.SHOPEE))
    s.append(make_obs(canonical_sku="A", platform=Platform.SHOPEE, observed_at=t_at(10)))
    s.append(make_obs(canonical_sku="A", platform=Platform.LAZADA))
    # 2 unique (sku, platform) pairs.
    assert s.n_series == 2
