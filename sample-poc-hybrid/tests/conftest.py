"""Pytest fixtures shared across unit + integration tests.

The `spark` fixture is module-scoped + Delta-aware so individual tests
don't pay the JVM startup cost. Path injection lets us import
`pipeline.spark_jobs.lib.*` directly from the source tree (no install).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_LIB = REPO_ROOT / "pipeline" / "spark_jobs"

# Make `from lib.X import Y` importable from anywhere in tests.
if str(PIPELINE_LIB) not in sys.path:
    sys.path.insert(0, str(PIPELINE_LIB))

# Force Java to behave inside hermetic test runs without docker.
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)


def pytest_collection_modifyitems(config, items):
    """Skip slow tests by default; opt in with `pytest -m slow`."""
    if config.getoption("-m") and "slow" in config.getoption("-m"):
        return
    skip_slow = pytest.mark.skip(reason="slow integration; run with `pytest -m slow`")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture(scope="module")
def warehouse_dir():
    """Per-test-module ephemeral Delta warehouse."""
    path = tempfile.mkdtemp(prefix="hybrid-warehouse-")
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="module")
def spark(warehouse_dir):
    """SparkSession with Delta + warehouse pointed at a temp dir.

    Module scope: pay JVM startup once per test file, not per test.
    """
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.appName("hybrid-tests")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", warehouse_dir)
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    spark.stop()
