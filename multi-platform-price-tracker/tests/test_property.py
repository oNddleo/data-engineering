"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from multiprice.detectors import detect_stockouts
from multiprice.io_jsonl import mapping_from_dict, mapping_to_dict, obs_from_dict, obs_to_dict
from multiprice.mapping import SkuRegistry
from multiprice.schema import Platform
from multiprice.store import ObservationStore

from ._fixtures import make_mapping, make_obs


@given(price=st.integers(min_value=1, max_value=10**11))
def test_obs_round_trips(price):
    o = make_obs(price=price, original_price=price)
    assert obs_from_dict(obs_to_dict(o)) == o


@given(
    sku=st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=65, max_codepoint=90))
)
def test_mapping_round_trips(sku):
    m = make_mapping(canonical_sku=sku)
    assert mapping_from_dict(mapping_to_dict(m)) == m


@given(n=st.integers(min_value=0, max_value=20))
def test_store_handles_n_appends(n):
    s = ObservationStore()
    for i in range(n):
        s.append(make_obs(canonical_sku=f"S-{i}"))
    assert len(s) == n


@given(in_stock=st.booleans())
def test_stockout_iff_zero_stock(in_stock):
    s = ObservationStore()
    s.append(make_obs(stock=10 if in_stock else 0))
    events = detect_stockouts(s)
    if in_stock:
        assert events == []
    else:
        assert len(events) == 1


@given(
    canonical_skus=st.lists(
        st.text(
            min_size=1, max_size=10, alphabet=st.characters(min_codepoint=65, max_codepoint=90)
        ),
        min_size=0,
        max_size=10,
        unique=True,
    )
)
def test_registry_n_skus_matches_unique_inputs(canonical_skus):
    r = SkuRegistry()
    for i, sku in enumerate(canonical_skus):
        r.register(
            make_mapping(canonical_sku=sku, platform=Platform.SHOPEE, platform_item_id=f"sp-{i}")
        )
    assert r.n_skus == len(canonical_skus)
