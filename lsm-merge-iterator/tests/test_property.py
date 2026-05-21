"""Hypothesis property tests for k-way merge."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from lsmmerge.merge import merge_runs
from lsmmerge.schema import Record


def _sorted_run(records: list[Record]) -> list[Record]:
    """Sort a list of records and renumber seq to be globally unique."""
    by_key: dict[str, Record] = {}
    for r in sorted(records, key=lambda r: (r.key, r.seq)):
        # Within the same run, later seq of same key wins inside the run.
        by_key[r.key] = r
    return sorted(by_key.values(), key=lambda r: r.key)


@given(
    st.lists(
        st.lists(
            st.tuples(
                st.text(alphabet="abcde", min_size=1, max_size=2),
                st.integers(min_value=0, max_value=100),
            ),
            min_size=0,
            max_size=15,
        ),
        min_size=0,
        max_size=5,
    ),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_merge_output_sorted_and_unique_keys(
    runs_raw: list[list[tuple[str, int]]],
) -> None:
    """Merged output is sorted by key and has no duplicate keys."""
    # Build runs with unique (key,seq) per run, globally-unique seq across runs.
    seq = 0
    runs: list[list[Record]] = []
    for run in runs_raw:
        recs: list[Record] = []
        seen_keys: set[str] = set()
        for k, _ in sorted(run, key=lambda kv: kv[0]):
            if k in seen_keys:
                continue
            seen_keys.add(k)
            seq += 1
            recs.append(Record(key=k, seq=seq, value=f"v{seq}"))
        runs.append(recs)

    out = list(merge_runs(runs))
    keys = [r.key for r in out]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))


@given(
    st.lists(
        st.tuples(
            st.text(alphabet="abc", min_size=1, max_size=1),
            st.integers(min_value=0, max_value=50),
        ),
        min_size=0,
        max_size=20,
    ),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_last_write_wins(pairs: list[tuple[str, int]]) -> None:
    """For each key, the merged output carries the highest seq seen."""
    # Build single-record runs (each run trivially sorted).
    runs = [[Record(key=k, seq=s, value=f"v{s}")] for k, s in pairs]
    out = {r.key: r for r in merge_runs(runs)}

    # Compute expected winner per key.
    expected: dict[str, int] = {}
    for k, s in pairs:
        expected[k] = max(expected.get(k, -1), s)

    for k, max_seq in expected.items():
        assert out[k].seq == max_seq, f"key {k!r}: got {out[k].seq}, want {max_seq}"


@given(
    st.lists(
        st.tuples(
            st.text(alphabet="abc", min_size=1, max_size=1),
            st.integers(min_value=0, max_value=50),
            st.booleans(),
        ),
        min_size=0,
        max_size=20,
    ),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_tombstone_consumption(triples: list[tuple[str, int, bool]]) -> None:
    """If the highest-seq record for a key is a tombstone, it drops in
    final-level compaction; if not, the key survives."""
    runs = [[Record(key=k, seq=s, value="" if t else f"v{s}", tombstone=t)] for k, s, t in triples]
    out_keep = {r.key: r for r in merge_runs(runs, keep_tombstones=True)}
    out_drop = {r.key: r for r in merge_runs(runs, keep_tombstones=False)}

    # keep_tombstones=True should be a superset of keep_tombstones=False.
    for k in out_drop:
        assert k in out_keep
        assert not out_keep[k].tombstone

    # Every dropped key (in out_keep but not out_drop) must be a tombstone.
    for k, rec in out_keep.items():
        if k not in out_drop:
            assert rec.tombstone
