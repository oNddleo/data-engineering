"""k-way merge correctness."""

from __future__ import annotations

import pytest

from lsmmerge.merge import merge_runs
from lsmmerge.schema import Record


def test_single_run_passthrough() -> None:
    run = [Record(key="a", seq=1, value="1"), Record(key="b", seq=2, value="2")]
    assert list(merge_runs([run])) == run


def test_empty_runs() -> None:
    assert list(merge_runs([])) == []
    assert list(merge_runs([[], []])) == []


def test_two_disjoint_runs_interleave() -> None:
    r1 = [Record(key="a", seq=1, value="A"), Record(key="c", seq=3, value="C")]
    r2 = [Record(key="b", seq=2, value="B"), Record(key="d", seq=4, value="D")]
    out = list(merge_runs([r1, r2]))
    assert [r.key for r in out] == ["a", "b", "c", "d"]


def test_duplicate_key_higher_seq_wins() -> None:
    older = [Record(key="a", seq=1, value="OLD")]
    newer = [Record(key="a", seq=2, value="NEW")]
    out = list(merge_runs([older, newer]))
    assert out == [Record(key="a", seq=2, value="NEW")]


def test_duplicate_key_higher_seq_wins_reversed_input() -> None:
    """The run order in the input list doesn't change the winner."""
    older = [Record(key="a", seq=1, value="OLD")]
    newer = [Record(key="a", seq=2, value="NEW")]
    out = list(merge_runs([newer, older]))
    assert out == [Record(key="a", seq=2, value="NEW")]


def test_tombstone_drops_key_by_default() -> None:
    older = [Record(key="a", seq=1, value="X")]
    tomb = [Record(key="a", seq=2, tombstone=True)]
    assert list(merge_runs([older, tomb])) == []


def test_tombstone_preserved_when_requested() -> None:
    older = [Record(key="a", seq=1, value="X")]
    tomb = [Record(key="a", seq=2, tombstone=True)]
    out = list(merge_runs([older, tomb], keep_tombstones=True))
    assert out == [Record(key="a", seq=2, tombstone=True)]


def test_older_tombstone_shadowed_by_newer_value() -> None:
    """A resurrected key (newer put after older delete) survives."""
    tomb = [Record(key="a", seq=1, tombstone=True)]
    newer = [Record(key="a", seq=2, value="RESURRECTED")]
    assert list(merge_runs([tomb, newer])) == [
        Record(key="a", seq=2, value="RESURRECTED"),
    ]


def test_three_way_merge() -> None:
    r1 = [Record(key="a", seq=1), Record(key="d", seq=4)]
    r2 = [Record(key="b", seq=2), Record(key="e", seq=5)]
    r3 = [Record(key="c", seq=3), Record(key="f", seq=6)]
    out = list(merge_runs([r1, r2, r3]))
    assert [r.key for r in out] == ["a", "b", "c", "d", "e", "f"]


def test_run_not_sorted_raises() -> None:
    bad = [Record(key="b", seq=1), Record(key="a", seq=2)]
    with pytest.raises(ValueError):
        list(merge_runs([bad]))


def test_streaming_iterator_input() -> None:
    """Merge should accept any iterable, not just lists."""

    def gen() -> object:
        yield Record(key="a", seq=1, value="A")
        yield Record(key="b", seq=2, value="B")

    out = list(merge_runs([gen()]))  # type: ignore[list-item]
    assert [r.key for r in out] == ["a", "b"]


def test_winner_value_is_full_record() -> None:
    """The emitted record carries the winning seq + value, not just key."""
    r1 = [Record(key="a", seq=1, value="v1")]
    r2 = [Record(key="a", seq=5, value="v5")]
    r3 = [Record(key="a", seq=3, value="v3")]
    out = list(merge_runs([r1, r2, r3]))
    assert out == [Record(key="a", seq=5, value="v5")]


def test_intra_run_duplicates_higher_seq_wins() -> None:
    """If a single run has the same key twice (unusual but allowed),
    the higher-seq record still wins. We require non-decreasing keys,
    so seq must be ascending within the duplicate group."""
    run = [Record(key="a", seq=1, value="v1"), Record(key="a", seq=2, value="v2")]
    out = list(merge_runs([run]))
    assert out == [Record(key="a", seq=2, value="v2")]
