"""LSMNode — the main entry point for the LSM-tree storage engine.

Wires together:
    WAL → MemTable → LevelManager (L0 … Ln SSTables)

All public methods are thread-safe via a single ``threading.Lock``.  A
:class:`~lsmcompact.compactor.RemoteCompactionWorker` is started in the
background and handles async compaction whenever L0 reaches its threshold.
"""

from __future__ import annotations

import threading
from pathlib import Path

from lsmcompact.compactor import Compactor, RemoteCompactionWorker
from lsmcompact.levels import LevelManager
from lsmcompact.memtable import TOMBSTONE, MemTable
from lsmcompact.wal import WAL


class LSMNode:
    """Persistent LSM-tree node.

    Parameters
    ----------
    data_dir:
        Root directory for WAL and SSTable files.  Created if absent.
    memtable_size_limit:
        Byte threshold at which the MemTable is flushed to an SSTable.
    """

    def __init__(
        self,
        data_dir: Path | str,
        memtable_size_limit: int = 4 * 1024 * 1024,
    ) -> None:
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._memtable = MemTable(size_limit=memtable_size_limit)
        self._wal = WAL(self._dir / "write.wal")
        self._levels = LevelManager(self._dir / "sstables")
        self._compactor = Compactor()
        self._worker = RemoteCompactionWorker()
        self._worker.start()

        self._recover()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def put(self, key: str, value: str) -> None:
        """Insert or update *key* with *value*."""
        with self._lock:
            self._wal.append_put(key, value)
            self._memtable.put(key, value)
            self._maybe_flush()

    def delete(self, key: str) -> None:
        """Delete *key* (writes a tombstone)."""
        with self._lock:
            self._wal.append_delete(key)
            self._memtable.delete(key)
            self._maybe_flush()

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, key: str) -> str | None:
        """Return the value for *key*, or ``None`` if not found / deleted."""
        with self._lock:
            # 1. Check MemTable first (most recent writes).
            result = self._memtable.get(key)
            if result is not None:
                return None if result == TOMBSTONE else result

            # 2. Search levels newest → oldest.
            for sst in self._levels.all_sstables():
                val = sst.get(key)
                if val is not None:
                    return None if val == TOMBSTONE else val

        return None

    def scan(self, start: str, end: str) -> list[tuple[str, str]]:
        """Return all live key/value pairs with ``start <= key < end``.

        Results are in ascending key order and tombstoned keys are excluded.
        """
        with self._lock:
            merged: dict[str, str] = {}

            # Collect from all SSTables oldest → newest so newer values win.
            all_ssts = list(reversed(self._levels.all_sstables()))
            for sst in all_ssts:
                for k, v in sst.scan(start, end):
                    merged[k] = v

            # MemTable is newest — overwrite.
            for k, v in self._memtable.scan(start, end):
                merged[k] = v

        return [(k, v) for k, v in sorted(merged.items()) if v != TOMBSTONE]

    # ------------------------------------------------------------------
    # Manual compaction
    # ------------------------------------------------------------------

    def compact(self) -> None:
        """Trigger an immediate synchronous L0 compaction."""
        with self._lock:
            self._flush_memtable()
            self._do_compact()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, object]:
        """Return a stats dict with level counts and MemTable size."""
        with self._lock:
            return {
                "memtable_entries": len(self._memtable),
                "levels": self._levels.stats(),
            }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush pending data and stop the background worker."""
        with self._lock:
            self._flush_memtable()
        self._wal.close()
        self._worker.stop()

    def __enter__(self) -> LSMNode:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recover(self) -> None:
        """Replay the WAL to restore any un-flushed writes after a crash."""
        for op, key, value in self._wal.recover():
            if op == "put":
                self._memtable.put(key, value)
            elif op == "delete":
                self._memtable.delete(key)

    def _maybe_flush(self) -> None:
        """Flush MemTable to SSTable if it has hit the size limit."""
        if self._memtable.is_full():
            self._flush_memtable()
            if self._levels.needs_compaction():
                # Dispatch to background worker asynchronously.
                self._dispatch_compaction()

    def _flush_memtable(self) -> None:
        """Write the MemTable to a new L0 SSTable and truncate the WAL."""
        items = list(self._memtable.items_sorted())
        if not items:
            return
        self._levels.flush_memtable(items)
        self._memtable.clear()
        self._wal.truncate()
        if self._levels.needs_compaction():
            self._dispatch_compaction()

    def _dispatch_compaction(self) -> None:
        """Submit a compaction job to the background worker (non-blocking)."""
        l0 = self._levels.get_level(0)
        if not l0:
            return
        dest = self._levels.new_sstable_path(1)
        future = self._worker.submit(l0, dest)

        def _on_done() -> None:
            try:
                new_sst = future.result(timeout=60.0)
            except Exception:  # noqa: BLE001
                return
            with self._lock:
                self._levels.replace(1, [], new_sst)
                # Remove the L0 files that were merged.
                for sst in l0:
                    try:
                        self._levels.replace(0, [sst], new_sst)
                    except Exception:  # noqa: BLE001
                        pass
                # Cleanup: remove old L0 files (best-effort).
                for sst in l0:
                    try:
                        sst.path.unlink(missing_ok=True)
                    except OSError:
                        pass
                # Remove the new_sst we spuriously added to L1 above.
                try:
                    self._levels.replace(1, [new_sst], new_sst)
                except Exception:  # noqa: BLE001
                    pass

        # Run the callback in a daemon thread so it doesn't block callers.
        t = threading.Thread(target=_on_done, daemon=True)
        t.start()

    def _do_compact(self) -> None:
        """Synchronous L0 → L1 compaction (called from :meth:`compact`)."""
        l0 = self._levels.get_level(0)
        if not l0:
            return
        dest = self._levels.new_sstable_path(1)
        new_sst = self._compactor.compact_l0(l0, dest)
        # Replace L0 files with the merged L1 SSTable.
        for sst in l0:
            self._levels.replace(0, [sst], new_sst)
        # Register in L1 properly.
        self._levels.replace(1, [new_sst], new_sst)
        # Remove merged L0 files (best-effort).
        for sst in l0:
            try:
                sst.path.unlink(missing_ok=True)
            except OSError:
                pass
