"""Compactor — merge-sort SSTables and manage compaction strategies.

Two strategies are implemented:

* **Size-tiered** (``SizeTieredCompactor``): merge *all* L0 SSTables into a
  single L1 SSTable.  Suitable for write-heavy workloads.
* **Leveled** (``LeveledCompactor``): pick the largest SSTable in Ln and merge
  it with any overlapping SSTables in Ln+1, producing a new sorted run in
  Ln+1.

Both strategies are exposed through the unified :class:`Compactor` facade which
also hosts :class:`RemoteCompactionWorker` — a ``threading.Thread`` that
performs compaction asynchronously.
"""

from __future__ import annotations

import heapq
import threading
import time
from typing import TYPE_CHECKING

from lsmcompact.memtable import TOMBSTONE
from lsmcompact.sstable import SSTable, SSTableWriter

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


# ---------------------------------------------------------------------------
# Low-level merge helpers
# ---------------------------------------------------------------------------


def merge_sstables(
    sources: list[SSTable],
    dest: Path,
    drop_tombstones: bool = False,
) -> SSTable:
    """Merge-sort *sources* into a single SSTable at *dest*.

    Rules:
    * When the same key appears in multiple sources the **latest** copy wins
      (sources are assumed ordered newest → oldest).
    * Tombstones are propagated unless *drop_tombstones* is ``True`` (set this
      only when merging into the bottom level with no older data).

    Returns the new :class:`SSTable`.
    """
    # We need newest-wins semantics.  Assign each source a priority equal to
    # its position in the list (lower index == higher priority == newer).
    # heapq gives us the *smallest* element first so we negate the priority.

    # Build iterators — each yields (key, value, priority, source_index).
    # We use a heap of (key, priority, value) where priority is 0-based index
    # with lower == newer (higher precedence).

    iters = [src.items() for src in sources]

    # Heap entries: (key, source_index, value)
    # When keys are equal we want the *smallest* source_index (newest).
    heap: list[tuple[str, int, str]] = []
    iter_state: list[Iterator[tuple[str, str]]] = list(iters)

    for i, it in enumerate(iter_state):
        try:
            k, v = next(it)
            heapq.heappush(heap, (k, i, v))
        except StopIteration:
            pass

    seen: set[str] = set()

    with SSTableWriter(dest) as writer:
        while heap:
            key, src_idx, value = heapq.heappop(heap)

            # Advance that source's iterator.
            try:
                nk, nv = next(iter_state[src_idx])
                heapq.heappush(heap, (nk, src_idx, nv))
            except StopIteration:
                pass

            if key in seen:
                # A newer version was already written — skip this older copy.
                continue
            seen.add(key)

            if drop_tombstones and value == TOMBSTONE:
                continue

            writer.write(key, value)

    return SSTable(dest)


# ---------------------------------------------------------------------------
# Size-tiered strategy
# ---------------------------------------------------------------------------


class SizeTieredCompactor:
    """Merge all L0 SSTables into a new L1 SSTable."""

    def compact(
        self,
        l0_ssts: list[SSTable],
        dest: Path,
    ) -> SSTable:
        """Merge *l0_ssts* (newest first) into *dest*."""
        return merge_sstables(l0_ssts, dest, drop_tombstones=False)


# ---------------------------------------------------------------------------
# Leveled strategy
# ---------------------------------------------------------------------------


class LeveledCompactor:
    """Pick and compact one SSTable from Ln into Ln+1."""

    def compact(
        self,
        ln_ssts: list[SSTable],
        ln1_ssts: list[SSTable],
        dest: Path,
    ) -> SSTable:
        """Merge *ln_ssts* and overlapping *ln1_ssts* into *dest*.

        *ln_ssts* are treated as newer (priority 0), *ln1_ssts* as older.
        Tombstones are dropped only if both source lists are exhausted at the
        bottom-most level — callers can pass ``drop_tombstones=True`` when
        appropriate; here we always keep them for safety.
        """
        sources = ln_ssts + ln1_ssts
        return merge_sstables(sources, dest, drop_tombstones=False)


# ---------------------------------------------------------------------------
# Remote compaction worker
# ---------------------------------------------------------------------------


class RemoteCompactionWorker(threading.Thread):
    """Background thread that drains a queue of compaction tasks.

    In a real system this would delegate to a remote gRPC worker.  Here we
    simulate that by executing the merge-sort locally but asynchronously in a
    separate :class:`threading.Thread`.

    Usage::

        worker = RemoteCompactionWorker()
        worker.start()
        future = worker.submit(sources, dest)
        result_sst = future.result()  # blocks until done
        worker.stop()
    """

    def __init__(self, poll_interval: float = 0.01) -> None:
        super().__init__(daemon=True, name="RemoteCompactionWorker")
        self._queue: list[
            tuple[list[SSTable], Path, threading.Event, list[SSTable | Exception]]
        ] = []
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._stop_flag = threading.Event()
        self._poll_interval = poll_interval

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(
        self,
        sources: list[SSTable],
        dest: Path,
    ) -> _CompactionFuture:
        """Schedule a merge of *sources* into *dest*.

        Returns a :class:`_CompactionFuture` that the caller can block on.
        """
        done_event: threading.Event = threading.Event()
        result_slot: list[SSTable | Exception] = []
        task = (sources, dest, done_event, result_slot)
        with self._cond:
            self._queue.append(task)
            self._cond.notify()
        return _CompactionFuture(done_event, result_slot)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the worker to stop and wait for it to finish."""
        self._stop_flag.set()
        with self._cond:
            self._cond.notify()
        self.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Thread body
    # ------------------------------------------------------------------

    def run(self) -> None:
        while not self._stop_flag.is_set():
            task = self._next_task()
            if task is None:
                time.sleep(self._poll_interval)
                continue
            sources, dest, done_event, result_slot = task
            try:
                sst = merge_sstables(sources, dest)
                result_slot.append(sst)
            except Exception as exc:  # noqa: BLE001
                result_slot.append(exc)
            finally:
                done_event.set()

    def _next_task(
        self,
    ) -> tuple[list[SSTable], Path, threading.Event, list[SSTable | Exception]] | None:
        with self._cond:
            if self._queue:
                return self._queue.pop(0)
            self._cond.wait(timeout=self._poll_interval)
            if self._queue:
                return self._queue.pop(0)
        return None


class _CompactionFuture:
    """Minimal future-like object returned by :meth:`RemoteCompactionWorker.submit`."""

    def __init__(
        self,
        event: threading.Event,
        result_slot: list[SSTable | Exception],
    ) -> None:
        self._event = event
        self._result_slot = result_slot

    def result(self, timeout: float | None = None) -> SSTable:
        """Block until the compaction finishes, then return the new SSTable."""
        self._event.wait(timeout=timeout)
        if not self._result_slot:
            raise TimeoutError("Compaction did not finish in time")
        outcome = self._result_slot[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


# ---------------------------------------------------------------------------
# Unified facade
# ---------------------------------------------------------------------------


class Compactor:
    """Facade that coordinates compaction across all levels.

    Ties together :class:`SizeTieredCompactor` (L0 → L1) and
    :class:`LeveledCompactor` (L1 → L2+).
    """

    def __init__(self) -> None:
        self._size_tiered = SizeTieredCompactor()
        self._leveled = LeveledCompactor()

    def compact_l0(self, l0_ssts: list[SSTable], dest: Path) -> SSTable:
        """Merge all L0 SSTables into a new L1 SSTable."""
        # Newest is *last* in the list (L0 appends in write order); reverse.
        return self._size_tiered.compact(list(reversed(l0_ssts)), dest)

    def compact_level(
        self,
        ln_ssts: list[SSTable],
        ln1_ssts: list[SSTable],
        dest: Path,
    ) -> SSTable:
        """Merge SSTables from Ln into Ln+1."""
        return self._leveled.compact(list(reversed(ln_ssts)), list(reversed(ln1_ssts)), dest)
