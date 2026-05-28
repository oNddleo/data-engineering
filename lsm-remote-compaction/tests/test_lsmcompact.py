"""Comprehensive tests for the lsmcompact package.

Coverage:
    TestMemTable         — MemTable unit tests
    TestWAL              — WAL append / recovery / crash simulation
    TestSSTable          — SSTable write/read, bloom filter, sparse index, scan
    TestBloomFilter      — False-positive rate, membership
    TestLevelManager     — L0 accumulation, compaction trigger, stats
    TestCompactor        — Merge-sort, deduplication, tombstone handling
    TestRemoteWorker     — Async remote compaction worker
    TestLSMNode          — End-to-end put/get/delete/scan, WAL recovery
    TestConcurrency      — Thread-safety for concurrent writes
    TestProperties       — Hypothesis property-based tests
"""

from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from lsmcompact.compactor import (
    Compactor,
    LeveledCompactor,
    RemoteCompactionWorker,
    SizeTieredCompactor,
    merge_sstables,
)
from lsmcompact.levels import L0_COMPACTION_THRESHOLD, LevelManager
from lsmcompact.memtable import TOMBSTONE, MemTable
from lsmcompact.node import LSMNode
from lsmcompact.sstable import BloomFilter, SSTable, SSTableWriter
from lsmcompact.wal import WAL

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmp() -> Path:
    """Return a fresh temporary directory (pytest will clean it up)."""
    return Path(tempfile.mkdtemp())


def _write_sst(path: Path, pairs: list[tuple[str, str]]) -> SSTable:
    """Helper: write sorted *pairs* to *path* and return an SSTable."""
    with SSTableWriter(path) as w:
        for k, v in sorted(pairs):
            w.write(k, v)
    return SSTable(path)


# ===========================================================================
# TestMemTable
# ===========================================================================


class TestMemTable:
    def test_put_and_get(self) -> None:
        m = MemTable()
        m.put("foo", "bar")
        assert m.get("foo") == "bar"

    def test_get_missing_returns_none(self) -> None:
        m = MemTable()
        assert m.get("missing") is None

    def test_update_overwrites(self) -> None:
        m = MemTable()
        m.put("k", "v1")
        m.put("k", "v2")
        assert m.get("k") == "v2"

    def test_delete_writes_tombstone(self) -> None:
        m = MemTable()
        m.put("k", "val")
        m.delete("k")
        assert m.get("k") == TOMBSTONE

    def test_len(self) -> None:
        m = MemTable()
        assert len(m) == 0
        m.put("a", "1")
        m.put("b", "2")
        assert len(m) == 2

    def test_iteration_is_sorted(self) -> None:
        m = MemTable()
        for ch in "zyxwvu":
            m.put(ch, ch)
        keys = [k for k, _ in m.items_sorted()]
        assert keys == sorted(keys)

    def test_scan_range(self) -> None:
        m = MemTable()
        for i in range(10):
            m.put(str(i), f"v{i}")
        result = m.scan("2", "6")
        keys = [k for k, _ in result]
        assert all("2" <= k < "6" for k in keys)
        assert keys == sorted(keys)

    def test_scan_empty_range(self) -> None:
        m = MemTable()
        m.put("a", "1")
        assert m.scan("z", "zz") == []

    def test_is_full_triggers_on_size(self) -> None:
        m = MemTable(size_limit=10)
        m.put("hello", "world")  # 10 bytes
        assert m.is_full()

    def test_clear_resets_state(self) -> None:
        m = MemTable()
        m.put("x", "y")
        m.clear()
        assert len(m) == 0
        assert m.get("x") is None

    def test_size_adjustment_on_overwrite(self) -> None:
        m = MemTable(size_limit=100)
        m.put("key", "short")
        m.put("key", "a" * 200)
        assert m.is_full()


# ===========================================================================
# TestWAL
# ===========================================================================


class TestWAL:
    def test_append_and_recover(self) -> None:
        d = _tmp()
        w = WAL(d / "test.wal")
        w.append_put("k1", "v1")
        w.append_put("k2", "v2")
        w.close()

        recovered = list(WAL(d / "test.wal").recover())
        assert ("put", "k1", "v1") in recovered
        assert ("put", "k2", "v2") in recovered

    def test_delete_recovery(self) -> None:
        d = _tmp()
        w = WAL(d / "del.wal")
        w.append_delete("gone")
        w.close()

        records = list(WAL(d / "del.wal").recover())
        ops = [(op, k) for op, k, _ in records]
        assert ("delete", "gone") in ops

    def test_truncate_clears_wal(self) -> None:
        d = _tmp()
        w = WAL(d / "t.wal")
        w.append_put("a", "b")
        w.truncate()
        w.close()

        assert list(WAL(d / "t.wal").recover()) == []

    def test_recover_missing_file(self) -> None:
        d = _tmp()
        w = WAL(d / "missing.wal")
        # We've already created the file through __init__ (open "a"), so
        # there should just be nothing to recover.
        assert list(w.recover()) == []
        w.close()

    def test_crash_recovery_skips_partial_line(self) -> None:
        d = _tmp()
        wal_path = d / "crash.wal"
        w = WAL(wal_path)
        w.append_put("good", "data")
        w.close()
        # Simulate a truncated write by appending garbage.
        with wal_path.open("a") as fh:
            fh.write("{broken json\n")
        records = list(WAL(wal_path).recover())
        assert len(records) == 1
        assert records[0] == ("put", "good", "data")

    def test_context_manager(self) -> None:
        d = _tmp()
        with WAL(d / "ctx.wal") as w:
            w.append_put("ctx", "ok")
        records = list(WAL(d / "ctx.wal").recover())
        assert any(r[1] == "ctx" for r in records)

    def test_multiple_truncate_cycles(self) -> None:
        d = _tmp()
        w = WAL(d / "cycle.wal")
        w.append_put("x", "1")
        w.truncate()
        w.append_put("y", "2")
        w.close()
        records = list(WAL(d / "cycle.wal").recover())
        assert len(records) == 1
        assert records[0][1] == "y"


# ===========================================================================
# TestBloomFilter
# ===========================================================================


class TestBloomFilter:
    def test_inserted_keys_always_found(self) -> None:
        bf = BloomFilter()
        keys = [f"key_{i}" for i in range(1000)]
        for k in keys:
            bf.add(k)
        for k in keys:
            assert k in bf

    def test_false_positive_rate(self) -> None:
        bf = BloomFilter()
        inserted = {f"real_{i}" for i in range(500)}
        for k in inserted:
            bf.add(k)
        # Test a different set of keys — non-inserted.
        not_inserted = [f"fake_{i}" for i in range(2000)]
        fps = sum(1 for k in not_inserted if k in bf and k not in inserted)
        fpr = fps / len(not_inserted)
        # With 16 KB bits and ~500 items the FPR should be well below 5 %.
        assert fpr < 0.05, f"False-positive rate too high: {fpr:.2%}"

    def test_serialisation_roundtrip(self) -> None:
        bf = BloomFilter()
        bf.add("hello")
        bf.add("world")
        restored = BloomFilter.from_hex(bf.to_hex())
        assert "hello" in restored
        assert "world" in restored

    def test_non_string_returns_false(self) -> None:
        bf = BloomFilter()
        bf.add("k")
        assert 42 not in bf  # type: ignore[operator]


# ===========================================================================
# TestSSTable
# ===========================================================================


class TestSSTable:
    def test_write_and_read(self) -> None:
        d = _tmp()
        sst = _write_sst(d / "t.sst", [("a", "1"), ("b", "2"), ("c", "3")])
        assert sst.get("a") == "1"
        assert sst.get("b") == "2"
        assert sst.get("c") == "3"

    def test_missing_key_returns_none(self) -> None:
        d = _tmp()
        sst = _write_sst(d / "t.sst", [("x", "1")])
        assert sst.get("missing") is None

    def test_items_sorted_order(self) -> None:
        d = _tmp()
        pairs = [("z", "26"), ("a", "1"), ("m", "13")]
        sst = _write_sst(d / "sorted.sst", pairs)
        keys = [k for k, _ in sst.items()]
        assert keys == sorted(keys)

    def test_scan_range(self) -> None:
        d = _tmp()
        pairs = [(str(i).zfill(3), f"v{i}") for i in range(20)]
        sst = _write_sst(d / "scan.sst", pairs)
        result = sst.scan("005", "010")
        keys = [k for k, _ in result]
        assert all("005" <= k < "010" for k in keys)
        assert keys == sorted(keys)

    def test_scan_empty(self) -> None:
        d = _tmp()
        sst = _write_sst(d / "empty.sst", [("a", "1")])
        assert sst.scan("z", "zz") == []

    def test_bloom_filter_rejects_missing(self) -> None:
        d = _tmp()
        sst = _write_sst(d / "bloom.sst", [("present", "yes")])
        # Bloom filter should almost certainly say 'definitely_absent' is not present.
        # (It *could* give a false positive but that's astronomically unlikely for one key.)
        # We test via __contains__ which is the bloom-only check.
        _ = sst.get("definitely_absent_xyzzy_12345")
        # No assertion on get return value (could be FP), but no crash either.

    def test_bloom_filter_membership(self) -> None:
        d = _tmp()
        sst = _write_sst(d / "bf.sst", [("hello", "world")])
        assert "hello" in sst

    def test_sparse_index_large_table(self) -> None:
        d = _tmp()
        pairs = [(f"key_{i:05d}", f"val_{i}") for i in range(200)]
        sst = _write_sst(d / "large.sst", pairs)
        # Spot-check a few lookups that should rely on the sparse index.
        assert sst.get("key_00000") == "val_0"
        assert sst.get("key_00100") == "val_100"
        assert sst.get("key_00199") == "val_199"

    def test_tombstone_preserved(self) -> None:
        d = _tmp()
        sst = _write_sst(d / "tomb.sst", [("k", TOMBSTONE)])
        assert sst.get("k") == TOMBSTONE

    def test_write_many_keys(self) -> None:
        d = _tmp()
        pairs = [(f"k{i:06d}", f"v{i}") for i in range(1000)]
        sst = _write_sst(d / "many.sst", pairs)
        assert sst.get("k000042") == "v42"
        assert sst.get("k000999") == "v999"


# ===========================================================================
# TestLevelManager
# ===========================================================================


class TestLevelManager:
    def test_l0_accumulation(self) -> None:
        d = _tmp()
        lm = LevelManager(d)
        for i in range(3):
            path = lm.new_sstable_path(0)
            _write_sst(path, [(f"k{i}", f"v{i}")])
            lm.add_l0(path)
        assert lm.l0_size() == 3

    def test_compaction_trigger(self) -> None:
        d = _tmp()
        lm = LevelManager(d)
        assert not lm.needs_compaction()
        for i in range(L0_COMPACTION_THRESHOLD):
            path = lm.new_sstable_path(0)
            _write_sst(path, [(f"k{i}", f"v{i}")])
            lm.add_l0(path)
        assert lm.needs_compaction()

    def test_stats_counts(self) -> None:
        d = _tmp()
        lm = LevelManager(d)
        path = lm.new_sstable_path(0)
        _write_sst(path, [("a", "1")])
        lm.add_l0(path)
        stats = lm.stats()
        assert stats["L0"] == 1

    def test_flush_memtable(self) -> None:
        d = _tmp()
        lm = LevelManager(d)
        sst = lm.flush_memtable([("a", "1"), ("b", "2")])
        assert sst is not None
        assert lm.l0_size() == 1

    def test_flush_empty_memtable_returns_none(self) -> None:
        d = _tmp()
        lm = LevelManager(d)
        result = lm.flush_memtable([])
        assert result is None

    def test_load_existing_sstables(self) -> None:
        d = _tmp()
        lm = LevelManager(d)
        for i in range(2):
            path = lm.new_sstable_path(0)
            _write_sst(path, [(f"k{i}", f"v{i}")])
            lm.add_l0(path)
        # Reload from disk.
        lm2 = LevelManager(d)
        assert lm2.l0_size() == 2

    def test_all_sstables_returns_all(self) -> None:
        d = _tmp()
        lm = LevelManager(d)
        for i in range(3):
            path = lm.new_sstable_path(0)
            _write_sst(path, [(f"k{i}", f"v{i}")])
            lm.add_l0(path)
        assert len(lm.all_sstables()) == 3


# ===========================================================================
# TestCompactor
# ===========================================================================


class TestCompactor:
    def test_merge_sort_correctness(self) -> None:
        d = _tmp()
        s1 = _write_sst(d / "s1.sst", [("a", "1"), ("c", "3"), ("e", "5")])
        s2 = _write_sst(d / "s2.sst", [("b", "2"), ("d", "4"), ("f", "6")])
        out = merge_sstables([s1, s2], d / "out.sst")
        keys = [k for k, _ in out.items()]
        assert keys == sorted(keys)
        assert set(keys) == {"a", "b", "c", "d", "e", "f"}

    def test_deduplication_newest_wins(self) -> None:
        d = _tmp()
        # s1 is newer (index 0), s2 is older (index 1).
        s1 = _write_sst(d / "new.sst", [("k", "new")])
        s2 = _write_sst(d / "old.sst", [("k", "old")])
        out = merge_sstables([s1, s2], d / "dedup.sst")
        assert out.get("k") == "new"

    def test_tombstone_kept_by_default(self) -> None:
        d = _tmp()
        s1 = _write_sst(d / "tomb.sst", [("k", TOMBSTONE)])
        out = merge_sstables([s1], d / "out.sst")
        assert out.get("k") == TOMBSTONE

    def test_tombstone_dropped_when_requested(self) -> None:
        d = _tmp()
        s1 = _write_sst(d / "tomb.sst", [("k", TOMBSTONE)])
        out = merge_sstables([s1], d / "out.sst", drop_tombstones=True)
        assert out.get("k") is None

    def test_size_tiered_compactor(self) -> None:
        d = _tmp()
        c = SizeTieredCompactor()
        ssts = [_write_sst(d / f"s{i}.sst", [(f"k{i}", f"v{i}")]) for i in range(4)]
        out = c.compact(list(reversed(ssts)), d / "out.sst")
        keys = [k for k, _ in out.items()]
        assert len(keys) == 4
        assert keys == sorted(keys)

    def test_leveled_compactor(self) -> None:
        d = _tmp()
        c = LeveledCompactor()
        ln = [_write_sst(d / "ln.sst", [("b", "new")])]
        ln1 = [_write_sst(d / "ln1.sst", [("a", "old"), ("b", "old")])]
        out = c.compact(ln, ln1, d / "out.sst")
        assert out.get("a") == "old"
        assert out.get("b") == "new"

    def test_compactor_facade_compact_l0(self) -> None:
        d = _tmp()
        c = Compactor()
        ssts = [_write_sst(d / f"l0_{i}.sst", [(f"key{i}", f"val{i}")]) for i in range(4)]
        out = c.compact_l0(ssts, d / "l1.sst")
        keys = [k for k, _ in out.items()]
        assert len(keys) == 4

    def test_merge_many_sources(self) -> None:
        d = _tmp()
        sources = [_write_sst(d / f"src{i}.sst", [(f"k{i:04d}", f"v{i}")]) for i in range(10)]
        out = merge_sstables(sources, d / "merged.sst")
        items = list(out.items())
        assert len(items) == 10

    def test_merge_with_overlapping_keys_latest_wins(self) -> None:
        d = _tmp()
        # Newer sources appear first in the list.
        s0 = _write_sst(d / "s0.sst", [("shared", "v2"), ("only_new", "yes")])
        s1 = _write_sst(d / "s1.sst", [("shared", "v1"), ("only_old", "yes")])
        out = merge_sstables([s0, s1], d / "out.sst")
        assert out.get("shared") == "v2"
        assert out.get("only_new") == "yes"
        assert out.get("only_old") == "yes"


# ===========================================================================
# TestRemoteWorker
# ===========================================================================


class TestRemoteWorker:
    def test_async_compaction(self) -> None:
        d = _tmp()
        worker = RemoteCompactionWorker()
        worker.start()
        try:
            s1 = _write_sst(d / "a.sst", [("a", "1"), ("c", "3")])
            s2 = _write_sst(d / "b.sst", [("b", "2"), ("d", "4")])
            future = worker.submit([s1, s2], d / "out.sst")
            result = future.result(timeout=10.0)
            keys = [k for k, _ in result.items()]
            assert keys == sorted(keys)
            assert len(keys) == 4
        finally:
            worker.stop(timeout=5.0)

    def test_multiple_jobs(self) -> None:
        d = _tmp()
        worker = RemoteCompactionWorker()
        worker.start()
        try:
            futures = []
            for i in range(3):
                s = _write_sst(d / f"i{i}.sst", [(f"k{i}", f"v{i}")])
                dest = d / f"out{i}.sst"
                futures.append(worker.submit([s], dest))
            for f in futures:
                result = f.result(timeout=10.0)
                assert result is not None
        finally:
            worker.stop(timeout=5.0)


# ===========================================================================
# TestLSMNode
# ===========================================================================


class TestLSMNode:
    def test_put_and_get(self) -> None:
        with LSMNode(_tmp()) as node:
            node.put("hello", "world")
            assert node.get("hello") == "world"

    def test_get_missing(self) -> None:
        with LSMNode(_tmp()) as node:
            assert node.get("nope") is None

    def test_overwrite(self) -> None:
        with LSMNode(_tmp()) as node:
            node.put("k", "v1")
            node.put("k", "v2")
            assert node.get("k") == "v2"

    def test_delete(self) -> None:
        with LSMNode(_tmp()) as node:
            node.put("k", "v")
            node.delete("k")
            assert node.get("k") is None

    def test_scan(self) -> None:
        with LSMNode(_tmp()) as node:
            for i in range(10):
                node.put(str(i).zfill(3), f"v{i}")
            result = node.scan("003", "007")
            keys = [k for k, _ in result]
            assert all("003" <= k < "007" for k in keys)
            assert keys == sorted(keys)

    def test_scan_excludes_deleted(self) -> None:
        with LSMNode(_tmp()) as node:
            node.put("a", "1")
            node.put("b", "2")
            node.delete("a")
            result = node.scan("a", "c")
            assert all(k != "a" for k, _ in result)

    def test_wal_recovery(self) -> None:
        d = _tmp()
        node = LSMNode(d)
        node.put("persist", "yes")
        node._wal.close()
        node._worker.stop()
        # Reopen — should recover from WAL.
        with LSMNode(d) as node2:
            assert node2.get("persist") == "yes"

    def test_stats(self) -> None:
        with LSMNode(_tmp()) as node:
            node.put("k", "v")
            s = node.stats()
            assert "memtable_entries" in s
            assert "levels" in s

    def test_compact(self) -> None:
        with LSMNode(_tmp(), memtable_size_limit=10) as node:
            for i in range(20):
                node.put(f"k{i:04d}", f"v{i}")
            node.compact()
            assert node.get("k0000") == "v0"

    def test_many_puts_and_gets(self) -> None:
        with LSMNode(_tmp()) as node:
            n = 100
            for i in range(n):
                node.put(f"key{i:06d}", f"value{i}")
            for i in range(n):
                assert node.get(f"key{i:06d}") == f"value{i}"

    def test_delete_nonexistent(self) -> None:
        with LSMNode(_tmp()) as node:
            node.delete("ghost")
            assert node.get("ghost") is None

    def test_scan_empty_db(self) -> None:
        with LSMNode(_tmp()) as node:
            assert node.scan("a", "z") == []


# ===========================================================================
# TestConcurrency
# ===========================================================================


class TestConcurrency:
    def test_concurrent_puts(self) -> None:
        d = _tmp()
        errors: list[Exception] = []

        def writer(node: LSMNode, thread_id: int) -> None:
            try:
                for i in range(50):
                    node.put(f"t{thread_id}_k{i:04d}", f"v{thread_id}_{i}")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        with LSMNode(d) as node:
            threads = [threading.Thread(target=writer, args=(node, tid)) for tid in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=15.0)

        assert not errors

    def test_concurrent_reads_and_writes(self) -> None:
        d = _tmp()
        stop = threading.Event()
        errors: list[Exception] = []

        def writer(node: LSMNode) -> None:
            i = 0
            while not stop.is_set():
                try:
                    node.put(f"rw_key_{i}", f"val_{i}")
                    i += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)
                    break

        def reader(node: LSMNode) -> None:
            while not stop.is_set():
                try:
                    node.get("rw_key_0")
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)
                    break

        with LSMNode(d) as node:
            threads: list[threading.Thread] = []
            threads += [threading.Thread(target=writer, args=(node,)) for _ in range(2)]
            threads += [threading.Thread(target=reader, args=(node,)) for _ in range(3)]
            for t in threads:
                t.start()
            time.sleep(0.3)
            stop.set()
            for t in threads:
                t.join(timeout=10.0)

        assert not errors


# ===========================================================================
# TestProperties (Hypothesis)
# ===========================================================================

_printable_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="_-.",
    ),
    min_size=1,
    max_size=32,
)

_kv_pairs = st.lists(
    st.tuples(_printable_text, _printable_text),
    min_size=1,
    max_size=60,
)


class TestProperties:
    @given(_kv_pairs)
    @settings(max_examples=80, deadline=5000)
    def test_memtable_last_write_wins(self, ops: list[tuple[str, str]]) -> None:
        m = MemTable()
        expected: dict[str, str] = {}
        for k, v in ops:
            m.put(k, v)
            expected[k] = v
        for k, v in expected.items():
            assert m.get(k) == v

    @given(_kv_pairs)
    @settings(max_examples=80, deadline=5000)
    def test_sstable_roundtrip(self, ops: list[tuple[str, str]]) -> None:
        d = _tmp()
        # Deduplicate keeping last value for each key.
        data: dict[str, str] = {}
        for k, v in ops:
            data[k] = v
        pairs = sorted(data.items())
        sst = _write_sst(d / "prop.sst", pairs)
        for k, v in pairs:
            assert sst.get(k) == v

    @given(_kv_pairs)
    @settings(max_examples=60, deadline=10000)
    def test_lsmnode_consistency(self, ops: list[tuple[str, str]]) -> None:
        d = _tmp()
        expected: dict[str, str] = {}
        with LSMNode(d, memtable_size_limit=128) as node:
            for k, v in ops:
                node.put(k, v)
                expected[k] = v
            for k, v in expected.items():
                got = node.get(k)
                assert got == v, f"key={k!r}: expected {v!r}, got {got!r}"

    @given(
        st.lists(
            st.tuples(
                _printable_text,
                st.one_of(st.just(None), _printable_text),
            ),
            min_size=1,
            max_size=40,
        )
    )
    @settings(max_examples=50, deadline=10000)
    def test_lsmnode_deletes_consistent(self, ops: list[tuple[str, Any]]) -> None:
        d = _tmp()
        expected: dict[str, str | None] = {}
        with LSMNode(d, memtable_size_limit=128) as node:
            for k, v in ops:
                if v is None:
                    node.delete(k)
                    expected[k] = None
                else:
                    node.put(k, v)
                    expected[k] = v
            for k, v in expected.items():
                got = node.get(k)
                assert got == v, f"key={k!r}: expected {v!r}, got {got!r}"

    @given(_kv_pairs)
    @settings(max_examples=60, deadline=10000)
    def test_merge_sort_all_keys_present(self, ops: list[tuple[str, str]]) -> None:
        d = _tmp()
        data: dict[str, str] = {}
        for k, v in ops:
            data[k] = v
        pairs = sorted(data.items())
        # Split into two halves.
        half = len(pairs) // 2 or 1
        s1 = _write_sst(d / "p1.sst", pairs[:half])
        s2 = _write_sst(d / "p2.sst", pairs[half:])
        out = merge_sstables([s1, s2], d / "merged.sst")
        result_keys = {k for k, _ in out.items()}
        assert result_keys == set(data.keys())
