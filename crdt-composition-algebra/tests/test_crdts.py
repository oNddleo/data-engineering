"""Unit tests for concrete CRDT implementations."""

from __future__ import annotations

from crdt.crdts import GCounter, GSet, LWWRegister, MVRegister, ORSet, PNCounter, TwoPSet


class TestGCounter:
    def test_initial_value_zero(self) -> None:
        assert GCounter.new().value() == 0

    def test_single_increment(self) -> None:
        c = GCounter.new().increment("n0")
        assert c.value() == 1

    def test_multi_node_increment(self) -> None:
        c = GCounter.new().increment("n0", 3).increment("n1", 2)
        assert c.value() == 5

    def test_merge_max(self) -> None:
        a = GCounter({"n0": 3, "n1": 1})
        b = GCounter({"n0": 1, "n1": 5})
        merged = a.merge(b)
        assert merged._counts == {"n0": 3, "n1": 5}
        assert merged.value() == 8

    def test_merge_idempotent(self) -> None:
        a = GCounter({"n0": 5})
        assert a.merge(a) == a

    def test_merge_commutative(self) -> None:
        a = GCounter({"n0": 3})
        b = GCounter({"n1": 7})
        assert a.merge(b) == b.merge(a)

    def test_merge_associative(self) -> None:
        a = GCounter({"n0": 1})
        b = GCounter({"n1": 2})
        c = GCounter({"n2": 3})
        assert a.merge(b).merge(c) == a.merge(b.merge(c))

    def test_partial_order(self) -> None:
        a = GCounter({"n0": 1})
        b = GCounter({"n0": 3})
        assert a <= b
        assert not b <= a


class TestPNCounter:
    def test_initial_zero(self) -> None:
        assert PNCounter.new().value() == 0

    def test_increment_decrement(self) -> None:
        pn = PNCounter.new().increment("n0", 5).decrement("n0", 2)
        assert pn.value() == 3

    def test_merge(self) -> None:
        a = PNCounter.new().increment("n0", 10)
        b = PNCounter.new().decrement("n1", 3)
        merged = a.merge(b)
        assert merged.value() == 7

    def test_merge_idempotent(self) -> None:
        a = PNCounter.new().increment("n0", 5).decrement("n0", 2)
        assert a.merge(a) == a

    def test_negative_value(self) -> None:
        pn = PNCounter.new().increment("n0", 2).decrement("n0", 5)
        assert pn.value() == -3


class TestLWWRegister:
    def test_write_and_read(self) -> None:
        reg: LWWRegister[str] = LWWRegister.new("hello", 1.0, "n0")
        assert reg.read() == "hello"

    def test_later_timestamp_wins(self) -> None:
        a: LWWRegister[str] = LWWRegister.new("old", 1.0, "n0")
        b: LWWRegister[str] = LWWRegister.new("new", 2.0, "n0")
        assert a.merge(b).read() == "new"
        assert b.merge(a).read() == "new"

    def test_tiebreak_on_node_id(self) -> None:
        a: LWWRegister[str] = LWWRegister.new("a", 1.0, "n0")
        b: LWWRegister[str] = LWWRegister.new("b", 1.0, "n1")
        # n1 > n0 lexicographically
        assert a.merge(b).read() == "b"

    def test_merge_idempotent(self) -> None:
        reg: LWWRegister[int] = LWWRegister.new(42, 1.0, "n0")
        assert reg.merge(reg) == reg


class TestGSet:
    def test_empty(self) -> None:
        assert len(GSet.new().elements()) == 0

    def test_add(self) -> None:
        s = GSet.new().add("a").add("b")
        assert s.elements() == frozenset({"a", "b"})

    def test_merge_union(self) -> None:
        a = GSet.new("x", "y")
        b = GSet.new("y", "z")
        merged = a.merge(b)
        assert merged.elements() == frozenset({"x", "y", "z"})

    def test_merge_idempotent(self) -> None:
        a = GSet.new("a", "b")
        assert a.merge(a) == a

    def test_partial_order(self) -> None:
        small = GSet.new("a")
        large = GSet.new("a", "b")
        assert small <= large
        assert not large <= small


class TestTwoPSet:
    def test_add_and_contains(self) -> None:
        s = TwoPSet.new().add("x")
        assert s.contains("x")

    def test_remove(self) -> None:
        s = TwoPSet.new().add("x").remove("x")
        assert not s.contains("x")

    def test_once_removed_cannot_readd(self) -> None:
        s = TwoPSet.new().add("x").remove("x").add("x")
        assert not s.contains("x")

    def test_merge(self) -> None:
        a = TwoPSet.new().add("x").add("y")
        b = TwoPSet.new().add("y").add("z")
        merged = a.merge(b)
        assert merged.contains("x")
        assert merged.contains("y")
        assert merged.contains("z")

    def test_merge_propagates_removals(self) -> None:
        a = TwoPSet.new().add("x")
        b = a.remove("x")
        merged = a.merge(b)
        assert not merged.contains("x")

    def test_merge_idempotent(self) -> None:
        a = TwoPSet.new().add("x").remove("x").add("y")
        assert a.merge(a) == a


class TestORSet:
    def test_add_element(self) -> None:
        s = ORSet.new().add("x", "n0")
        assert s.contains("x")

    def test_remove_element(self) -> None:
        s = ORSet.new().add("x", "n0").remove("x")
        assert not s.contains("x")

    def test_add_wins_over_concurrent_remove(self) -> None:
        # n0 adds x; n1 independently adds and removes x
        s_n0 = ORSet.new().add("x", "n0")
        s_n1 = ORSet.new().add("x", "n1").remove("x")
        # After merge, n0's add survives because n1 only tombstoned n1's token
        merged = s_n0.merge(s_n1)
        assert merged.contains("x")

    def test_merge_idempotent(self) -> None:
        s = ORSet.new().add("x", "n0").add("y", "n0")
        assert s.merge(s) == s

    def test_merge_commutative(self) -> None:
        a = ORSet.new().add("x", "n0")
        b = ORSet.new().add("y", "n1")
        assert a.merge(b) == b.merge(a)

    def test_elements_after_operations(self) -> None:
        s = ORSet.new().add("a", "n0").add("b", "n0").remove("a")
        assert s.elements() == frozenset({"b"})


class TestMVRegister:
    def test_write_and_read(self) -> None:
        r = MVRegister.new().write("hello", "n0")
        assert "hello" in r.read()

    def test_concurrent_writes_preserved(self) -> None:
        r1 = MVRegister.new().write("a", "n0")
        r2 = MVRegister.new().write("b", "n1")
        merged = r1.merge(r2)
        vals = set(merged.read())
        assert "a" in vals and "b" in vals

    def test_merge_idempotent(self) -> None:
        r = MVRegister.new().write("x", "n0")
        assert r.merge(r) == r
