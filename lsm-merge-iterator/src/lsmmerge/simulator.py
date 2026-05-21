"""Deterministic generator of overlapping sorted runs."""

from __future__ import annotations

import random

from lsmmerge.schema import Record


def generate_runs(
    n_runs: int = 3,
    keys_per_run: int = 20,
    key_universe: int = 50,
    tombstone_rate: float = 0.1,
    seed: int = 0,
) -> list[list[Record]]:
    """Generate ``n_runs`` sorted runs over a shared key universe.

    Sequence numbers are globally monotonic across all runs — the run
    written *later* (higher index) tends to win key collisions, which
    matches real LSM-tree behaviour (newer level shadows older).
    """
    if n_runs < 1:
        raise ValueError("n_runs must be >= 1")
    if keys_per_run < 0:
        raise ValueError("keys_per_run must be >= 0")
    if key_universe < 1:
        raise ValueError("key_universe must be >= 1")
    if not 0.0 <= tombstone_rate <= 1.0:
        raise ValueError("tombstone_rate must be in [0, 1]")

    rng = random.Random(seed)
    runs: list[list[Record]] = []
    seq = 0
    for r in range(n_runs):
        sample = sorted(rng.sample(range(key_universe), k=min(keys_per_run, key_universe)))
        records: list[Record] = []
        for k in sample:
            seq += 1
            is_tomb = rng.random() < tombstone_rate
            rec = Record(
                key=f"k{k:04d}",
                seq=seq,
                value="" if is_tomb else f"v{r}-{k}",
                tombstone=is_tomb,
            )
            records.append(rec)
        runs.append(records)
    return runs


__all__ = ["generate_runs"]
