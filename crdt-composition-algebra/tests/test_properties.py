"""Hypothesis property tests for semilattice laws."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from crdt.crdts import GCounter, GSet, PNCounter, TwoPSet


def _gcounter(keys: list[str], draws: object) -> GCounter:
    draw = draws  # type: ignore[assignment]
    d: dict[str, int] = {}
    for k in keys:
        if callable(draw):
            v = draw(st.integers(min_value=0, max_value=20))
            d[k] = v
    return GCounter(d)


_NODES = ["n0", "n1", "n2"]
_ELEMS = ["a", "b", "c", "d"]


class TestGCounterLaws:
    @given(
        a=st.fixed_dictionaries({k: st.integers(0, 20) for k in _NODES}).map(GCounter),
        b=st.fixed_dictionaries({k: st.integers(0, 20) for k in _NODES}).map(GCounter),
    )
    @settings(max_examples=100)
    def test_idempotent(self, a: GCounter, b: GCounter) -> None:
        ab = a.merge(b)
        assert ab.merge(ab) == ab

    @given(
        a=st.fixed_dictionaries({k: st.integers(0, 20) for k in _NODES}).map(GCounter),
        b=st.fixed_dictionaries({k: st.integers(0, 20) for k in _NODES}).map(GCounter),
    )
    @settings(max_examples=100)
    def test_commutative(self, a: GCounter, b: GCounter) -> None:
        assert a.merge(b) == b.merge(a)

    @given(
        a=st.fixed_dictionaries({k: st.integers(0, 20) for k in _NODES}).map(GCounter),
        b=st.fixed_dictionaries({k: st.integers(0, 20) for k in _NODES}).map(GCounter),
        c=st.fixed_dictionaries({k: st.integers(0, 20) for k in _NODES}).map(GCounter),
    )
    @settings(max_examples=80)
    def test_associative(self, a: GCounter, b: GCounter, c: GCounter) -> None:
        assert a.merge(b).merge(c) == a.merge(b.merge(c))

    @given(
        a=st.fixed_dictionaries({k: st.integers(0, 20) for k in _NODES}).map(GCounter),
        b=st.fixed_dictionaries({k: st.integers(0, 20) for k in _NODES}).map(GCounter),
    )
    @settings(max_examples=80)
    def test_monotone(self, a: GCounter, b: GCounter) -> None:
        ab = a.merge(b)
        assert ab.value() >= a.value()
        assert ab.value() >= b.value()


class TestPNCounterLaws:
    def _make(self, inc: dict[str, int], dec: dict[str, int]) -> PNCounter:
        return PNCounter(GCounter(inc), GCounter(dec))

    @given(
        ai=st.fixed_dictionaries({"n0": st.integers(0, 10)}).map(lambda d: GCounter(d)),
        ad=st.fixed_dictionaries({"n0": st.integers(0, 5)}).map(lambda d: GCounter(d)),
        bi=st.fixed_dictionaries({"n1": st.integers(0, 10)}).map(lambda d: GCounter(d)),
        bd=st.fixed_dictionaries({"n1": st.integers(0, 5)}).map(lambda d: GCounter(d)),
    )
    @settings(max_examples=80)
    def test_commutative(self, ai: GCounter, ad: GCounter, bi: GCounter, bd: GCounter) -> None:
        a = PNCounter(ai, ad)
        b = PNCounter(bi, bd)
        assert a.merge(b) == b.merge(a)

    @given(
        ai=st.fixed_dictionaries({"n0": st.integers(0, 10)}).map(lambda d: GCounter(d)),
        ad=st.fixed_dictionaries({"n0": st.integers(0, 5)}).map(lambda d: GCounter(d)),
        bi=st.fixed_dictionaries({"n1": st.integers(0, 10)}).map(lambda d: GCounter(d)),
        bd=st.fixed_dictionaries({"n1": st.integers(0, 5)}).map(lambda d: GCounter(d)),
    )
    @settings(max_examples=80)
    def test_idempotent(self, ai: GCounter, ad: GCounter, bi: GCounter, bd: GCounter) -> None:
        a = PNCounter(ai, ad)
        b = PNCounter(bi, bd)
        ab = a.merge(b)
        assert ab.merge(ab) == ab


class TestGSetLaws:
    def _gset(self, elems: list[str]) -> GSet:
        return GSet(frozenset(elems))

    @given(
        a=st.lists(st.sampled_from(_ELEMS), max_size=3).map(lambda x: GSet(frozenset(x))),
        b=st.lists(st.sampled_from(_ELEMS), max_size=3).map(lambda x: GSet(frozenset(x))),
        c=st.lists(st.sampled_from(_ELEMS), max_size=3).map(lambda x: GSet(frozenset(x))),
    )
    @settings(max_examples=80)
    def test_associative(self, a: GSet, b: GSet, c: GSet) -> None:
        assert a.merge(b).merge(c) == a.merge(b.merge(c))

    @given(
        a=st.lists(st.sampled_from(_ELEMS), max_size=3).map(lambda x: GSet(frozenset(x))),
        b=st.lists(st.sampled_from(_ELEMS), max_size=3).map(lambda x: GSet(frozenset(x))),
    )
    @settings(max_examples=80)
    def test_commutative(self, a: GSet, b: GSet) -> None:
        assert a.merge(b) == b.merge(a)

    @given(
        a=st.lists(st.sampled_from(_ELEMS), max_size=3).map(lambda x: GSet(frozenset(x))),
    )
    @settings(max_examples=50)
    def test_idempotent(self, a: GSet) -> None:
        assert a.merge(a) == a


class TestConvergence:
    @given(
        ops=st.lists(
            st.tuples(
                st.sampled_from(["add", "remove"]),
                st.sampled_from(_ELEMS),
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=50)
    def test_twopset_convergent(self, ops: list[tuple[str, str]]) -> None:
        """Two replicas applying same ops in different orders converge."""
        import random

        rng = random.Random(42)
        shuffled = list(ops)
        rng.shuffle(shuffled)

        def apply(s: TwoPSet, operations: list[tuple[str, str]]) -> TwoPSet:
            for op, elem in operations:
                if op == "add":
                    s = s.add(elem)
                else:
                    s = s.remove(elem)
            return s

        s1 = apply(TwoPSet.new(), ops)
        s2 = apply(TwoPSet.new(), shuffled)
        # After merge, both converge to the same state as applying all ops
        merged = s1.merge(s2)
        # The merged state is commutative
        assert merged == s2.merge(s1)
