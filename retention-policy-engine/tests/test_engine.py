"""Unit tests for retention engine."""

from __future__ import annotations

import pytest

from retention.engine import apply_policy
from retention.policy import Policy, PolicyKind
from retention.schema import Record


def _rec(key: str, age_ms: int, size: int = 1000, tags: frozenset[str] = frozenset()) -> Record:
    return Record(key=key, created_at_ms=1_000_000 - age_ms, size_bytes=size, tags=tags)


NOW = 1_000_000


class TestTTL:
    def test_all_fresh_kept(self) -> None:
        records = [_rec("a", 100), _rec("b", 200)]
        policy = Policy.ttl(ttl_ms=500)
        result = apply_policy(records, policy, now_ms=NOW)
        assert result.records_freed == 0
        assert len(result.kept) == 2

    def test_all_expired(self) -> None:
        records = [_rec("a", 1000), _rec("b", 2000)]
        policy = Policy.ttl(ttl_ms=500)
        result = apply_policy(records, policy, now_ms=NOW)
        assert result.records_freed == 2
        assert result.kept == []

    def test_partial_expired(self) -> None:
        records = [_rec("fresh", 100), _rec("old", 1000)]
        policy = Policy.ttl(ttl_ms=500)
        result = apply_policy(records, policy, now_ms=NOW)
        assert result.records_freed == 1
        assert result.kept[0].key == "fresh"

    def test_bytes_freed(self) -> None:
        records = [_rec("a", 1000, size=512), _rec("b", 1000, size=1024)]
        policy = Policy.ttl(ttl_ms=500)
        result = apply_policy(records, policy, now_ms=NOW)
        assert result.bytes_freed == 1536

    def test_tag_filter_exempt(self) -> None:
        hot = _rec("hot", 1000, tags=frozenset({"hot"}))
        cold = _rec("cold", 1000, tags=frozenset({"cold"}))
        policy = Policy.ttl(ttl_ms=500, tag_filter=frozenset({"cold"}))
        result = apply_policy([hot, cold], policy, now_ms=NOW)
        kept_keys = {r.key for r in result.kept}
        assert "hot" in kept_keys  # exempt
        assert "cold" not in kept_keys


class TestMaxCount:
    def test_keep_n_newest(self) -> None:
        records = [_rec(f"r{i}", age_ms=i * 100) for i in range(10)]
        policy = Policy.max_count(n=3)
        result = apply_policy(records, policy, now_ms=NOW)
        assert len(result.kept) == 3
        # newest three = age 0, 100, 200
        ages = {NOW - r.created_at_ms for r in result.kept}
        assert ages == {0, 100, 200}

    def test_fewer_than_max_all_kept(self) -> None:
        records = [_rec("a", 0), _rec("b", 100)]
        policy = Policy.max_count(n=5)
        result = apply_policy(records, policy, now_ms=NOW)
        assert result.records_freed == 0

    def test_evicted_count(self) -> None:
        records = [_rec(f"r{i}", i * 10) for i in range(20)]
        policy = Policy.max_count(n=10)
        result = apply_policy(records, policy, now_ms=NOW)
        assert result.records_freed == 10
        assert len(result.kept) == 10


class TestMaxSize:
    def test_within_limit(self) -> None:
        records = [_rec("a", 0, size=100), _rec("b", 100, size=200)]
        policy = Policy.max_size(max_bytes=1000)
        result = apply_policy(records, policy, now_ms=NOW)
        assert result.records_freed == 0

    def test_evict_oldest_to_fit(self) -> None:
        # 3 records, 500 bytes each, max 800 → evict oldest
        records = [
            _rec("new", 0, size=500),
            _rec("mid", 1000, size=500),
            _rec("old", 2000, size=500),
        ]
        policy = Policy.max_size(max_bytes=800)
        result = apply_policy(records, policy, now_ms=NOW)
        kept_keys = {r.key for r in result.kept}
        assert "new" in kept_keys
        assert result.bytes_freed > 0

    def test_bytes_freed_correct(self) -> None:
        records = [_rec(f"r{i}", i * 100, size=300) for i in range(5)]
        policy = Policy.max_size(max_bytes=700)
        result = apply_policy(records, policy, now_ms=NOW)
        assert result.bytes_freed == sum(r.size_bytes for r in result.evicted)


class TestComposite:
    def test_ttl_and_count(self) -> None:
        records = [_rec(f"r{i}", i * 100) for i in range(10)]
        # TTL evicts records older than 500ms; count keeps only 3
        p = Policy.composite(
            Policy.ttl(ttl_ms=500),
            Policy.max_count(n=3),
        )
        result = apply_policy(records, p, now_ms=NOW)
        # Union of evictions: at least count-evicted and ttl-evicted
        assert len(result.kept) <= 3

    def test_composite_requires_sub_policies(self) -> None:
        with pytest.raises(ValueError):
            Policy(kind=PolicyKind.COMPOSITE)


class TestPolicyValidation:
    def test_ttl_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            Policy(kind=PolicyKind.TTL, ttl_ms=0)

    def test_max_count_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            Policy(kind=PolicyKind.MAX_COUNT, count_limit=0)

    def test_max_size_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            Policy(kind=PolicyKind.MAX_SIZE, size_limit=0)


class TestSchema:
    def test_empty_key_raises(self) -> None:
        with pytest.raises(ValueError):
            Record(key="", created_at_ms=0, size_bytes=0)

    def test_negative_size_raises(self) -> None:
        with pytest.raises(ValueError):
            Record(key="k", created_at_ms=0, size_bytes=-1)

    def test_negative_created_at_raises(self) -> None:
        with pytest.raises(ValueError):
            Record(key="k", created_at_ms=-1, size_bytes=0)
