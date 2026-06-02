"""LevelManager — tracks SSTable files across levels.

Level layout
------------
* **L0** — overlapping SSTables written directly from MemTable flushes.
  Compaction is triggered when ``len(L0) >= L0_COMPACTION_THRESHOLD``.
* **L1+** — non-overlapping SSTables produced by the Compactor.

Each level is simply a list of :class:`~lsmcompact.sstable.SSTable` objects
ordered oldest → newest within L0, and by key-range within L1+.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from lsmcompact.sstable import SSTable, SSTableWriter

if TYPE_CHECKING:
    from pathlib import Path

L0_COMPACTION_THRESHOLD = 4  # trigger compaction when L0 has this many files
MAX_LEVELS = 7


class LevelManager:
    """Manages a multi-level hierarchy of SSTables on disk.

    Parameters
    ----------
    data_dir:
        Directory where SSTable files are stored.  Created if absent.
    """

    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        # _levels[0] == L0, _levels[1] == L1, …
        self._levels: list[list[SSTable]] = [[] for _ in range(MAX_LEVELS)]
        self._lock = threading.Lock()
        self._next_id = 0
        self._load_existing()

    # ------------------------------------------------------------------
    # SSTable lifecycle
    # ------------------------------------------------------------------

    def new_sstable_path(self, level: int) -> Path:
        """Return a fresh, unique path for a new SSTable at *level*."""
        with self._lock:
            fid = self._next_id
            self._next_id += 1
        return self._dir / f"L{level}_{fid:08d}.sst"

    def add_l0(self, path: Path) -> SSTable:
        """Register a flushed SSTable in L0."""
        sst = SSTable(path)
        with self._lock:
            self._levels[0].append(sst)
        return sst

    def replace(
        self,
        level: int,
        old_ssts: list[SSTable],
        new_sst: SSTable,
    ) -> None:
        """Atomically swap *old_ssts* for *new_sst* at *level*.

        Old files are removed from the list first; then *new_sst* is appended
        (L1+ will be re-sorted by key range afterwards).
        """
        with self._lock:
            lvl = self._levels[level]
            for sst in old_ssts:
                try:
                    lvl.remove(sst)
                except ValueError:
                    pass
            lvl.append(new_sst)

    def promote_to_level(self, from_level: int, sst: SSTable, to_level: int) -> None:
        """Move *sst* from *from_level* to *to_level*."""
        with self._lock:
            try:
                self._levels[from_level].remove(sst)
            except ValueError:
                pass
            self._levels[to_level].append(sst)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def l0_size(self) -> int:
        """Number of SSTables currently in L0."""
        with self._lock:
            return len(self._levels[0])

    def needs_compaction(self) -> bool:
        """Return ``True`` when L0 has reached the compaction threshold."""
        return self.l0_size() >= L0_COMPACTION_THRESHOLD

    def get_level(self, level: int) -> list[SSTable]:
        """Return a snapshot of the SSTables at *level*."""
        with self._lock:
            return list(self._levels[level])

    def all_sstables(self) -> list[SSTable]:
        """Return every SSTable across all levels (newest first within each level)."""
        with self._lock:
            result: list[SSTable] = []
            for lvl in self._levels:
                result.extend(reversed(lvl))
            return result

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        """Return per-level SSTable counts."""
        with self._lock:
            return {f"L{i}": len(lvl) for i, lvl in enumerate(self._levels)}

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def flush_memtable(self, items: list[tuple[str, str]]) -> SSTable | None:
        """Write *items* (sorted key/value pairs) as a new L0 SSTable.

        Returns the newly created :class:`SSTable`, or ``None`` if *items* is
        empty.
        """
        if not items:
            return None
        path = self.new_sstable_path(0)
        with SSTableWriter(path) as writer:
            for key, value in items:
                writer.write(key, value)
        return self.add_l0(path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_existing(self) -> None:
        """Scan *data_dir* and register any ``.sst`` files found."""
        sst_files = sorted(self._dir.glob("*.sst"))
        for p in sst_files:
            # Infer level from filename prefix L<n>_
            try:
                level = int(p.stem.split("_")[0][1:])
            except (IndexError, ValueError):
                level = 0
            level = min(level, MAX_LEVELS - 1)
            sst = SSTable(p)
            self._levels[level].append(sst)
            # Keep _next_id ahead of any existing file ids.
            try:
                fid = int(p.stem.split("_")[1])
                if fid >= self._next_id:
                    self._next_id = fid + 1
            except (IndexError, ValueError):
                pass
