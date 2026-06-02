"""Generate synthetic table metadata and query patterns for testing."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from compact.schema import DataFile, Partition, QueryPattern, TableMeta

_COLUMNS = ["event_date", "user_id", "country", "product_id", "category", "amount", "status"]


def _rand_file(
    rng: random.Random,
    partition_key: str,
    size_range: tuple[int, int],
    age_days_range: tuple[int, int],
) -> DataFile:
    now = datetime.now(tz=timezone.utc)
    days_old = rng.randint(*age_days_range)
    created = now - timedelta(days=days_old)
    modified = created + timedelta(hours=rng.randint(0, 12))
    size = rng.randint(*size_range)
    return DataFile(
        path=f"s3://bucket/table/{partition_key}/part-{rng.randint(0, 99999):05d}.parquet",
        size_bytes=size,
        row_count=size // 200,
        partition=partition_key,
        created_at=created,
        last_modified=modified,
    )


def generate_table(
    n_partitions: int = 20,
    files_per_partition_range: tuple[int, int] = (1, 30),
    small_file_fraction: float = 0.6,
    stale_partition_fraction: float = 0.1,
    seed: int | None = None,
    table_name: str = "events",
    fmt: str = "delta",
) -> TableMeta:
    """Generate a synthetic lakehouse table with realistic file size distribution."""
    rng = random.Random(seed)
    target = 128 * 1024 * 1024  # 128 MiB
    small_range = (1 * 1024 * 1024, int(target * 0.25))
    large_range = (target, 4 * target)
    stale_days = 100

    partitions: list[Partition] = []
    for i in range(n_partitions):
        date_str = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
        n_files = rng.randint(*files_per_partition_range)
        is_stale = rng.random() < stale_partition_fraction

        files: list[DataFile] = []
        for _ in range(n_files):
            if rng.random() < small_file_fraction:
                age_range = (stale_days + 10, stale_days + 60) if is_stale else (0, 30)
                f = _rand_file(rng, date_str, small_range, age_range)
            else:
                age_range = (stale_days + 10, stale_days + 60) if is_stale else (0, 30)
                f = _rand_file(rng, date_str, large_range, age_range)
            files.append(f)
        partitions.append(Partition(key=date_str, files=files))

    return TableMeta(
        table_name=table_name,
        format=fmt,
        partitions=partitions,
        columns=_COLUMNS[:],
    )


def generate_query_patterns(
    n_patterns: int = 50,
    seed: int | None = None,
) -> list[QueryPattern]:
    """Generate synthetic query access patterns."""
    rng = random.Random(seed)
    patterns: list[QueryPattern] = []
    for i in range(n_patterns):
        n_filter = rng.randint(1, 3)
        n_join = rng.randint(0, 2)
        n_group = rng.randint(0, 2)
        filter_cols = rng.sample(_COLUMNS, min(n_filter, len(_COLUMNS)))
        join_cols = rng.sample(_COLUMNS, min(n_join, len(_COLUMNS)))
        group_cols = rng.sample(_COLUMNS, min(n_group, len(_COLUMNS)))
        patterns.append(
            QueryPattern(
                query_id=f"q{i:04d}",
                filter_columns=filter_cols,
                join_columns=join_cols,
                group_by_columns=group_cols,
                frequency=rng.randint(1, 100),
            )
        )
    return patterns
