"""Tests for the high-level MetadataStore API."""

from __future__ import annotations

from raftmeta.store import MetadataStore


class TestMetadataStore:
    def _store(self, n: int = 3, seed: int = 1) -> MetadataStore:
        return MetadataStore(node_ids=[f"n{i}" for i in range(n)], seed=seed)

    def test_elects_leader_on_init(self) -> None:
        store = self._store()
        assert store.leader is not None

    def test_set_and_get(self) -> None:
        store = self._store()
        ok = store.set("greeting", "hello")
        assert ok is True
        assert store.get("greeting") == "hello"

    def test_get_missing_returns_none(self) -> None:
        store = self._store()
        assert store.get("nonexistent") is None

    def test_delete_key(self) -> None:
        store = self._store()
        store.set("temp", "123")
        store.delete("temp")
        assert store.get("temp") is None

    def test_overwrite_key(self) -> None:
        store = self._store()
        store.set("counter", "1")
        store.set("counter", "2")
        assert store.get("counter") == "2"

    def test_keys_returns_all(self) -> None:
        store = self._store()
        store.set("a", "1")
        store.set("b", "2")
        store.set("c", "3")
        ks = store.keys()
        assert set(ks) >= {"a", "b", "c"}

    def test_five_node_cluster(self) -> None:
        store = self._store(n=5, seed=7)
        assert store.leader is not None
        store.set("x", "99")
        assert store.get("x") == "99"
