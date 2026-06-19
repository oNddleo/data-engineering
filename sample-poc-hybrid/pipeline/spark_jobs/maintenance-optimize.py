"""Delta maintenance: OPTIMIZE (+ ZORDER) and VACUUM on bronze/silver tables.

Phase-05 validation Q3 settled the streaming-vs-maintenance race by having
Airflow's DAG 3 pause the IoT streaming DAG before this job runs. This
script itself is therefore safe to assume single-writer at runtime.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pyspark.sql import SparkSession

from lib.spark_session import build_streaming_session

LOG = logging.getLogger("maintenance-optimize")
APP_NAME = "delta-maintenance"


def load_config(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def optimize_table(spark: SparkSession, table: str, zorder_by: list[str] | None) -> None:
    if zorder_by:
        cols = ", ".join(zorder_by)
        spark.sql(f"OPTIMIZE {table} ZORDER BY ({cols})")
        LOG.info("OPTIMIZE %s ZORDER BY (%s)", table, cols)
    else:
        spark.sql(f"OPTIMIZE {table}")
        LOG.info("OPTIMIZE %s", table)


def vacuum_table(spark: SparkSession, table: str, retention_hours: int) -> None:
    # POC retention is intentionally 168h. Production should keep ≥ 7d.
    spark.sql(f"VACUUM {table} RETAIN {retention_hours} HOURS")
    LOG.info("VACUUM %s RETAIN %d HOURS", table, retention_hours)


def run(cfg: dict) -> int:
    spark = build_streaming_session(APP_NAME, stop_gracefully_on_shutdown=False)
    spark.sparkContext.setLogLevel("WARN")
    # Required for short VACUUM retention.
    spark.conf.set("spark.databricks.delta.retentionDurationCheck.enabled", "false")

    for spec in cfg.get("tables", []):
        table = spec["table"]
        try:
            optimize_table(spark, table, spec.get("zorder_by"))
        except Exception as e:  # noqa: BLE001
            LOG.warning("OPTIMIZE %s failed: %s", table, e)
        try:
            vacuum_table(spark, table, int(spec.get("retention_hours", 168)))
        except Exception as e:  # noqa: BLE001
            LOG.warning("VACUUM %s failed: %s", table, e)
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Delta maintenance.")
    default_cfg = os.environ.get(
        "MAINTENANCE_CONFIG",
        "/opt/hybrid/pipeline/conf/maintenance-optimize.yaml",
    )
    p.add_argument("--config", default=default_cfg)
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    cfg = load_config(args.config)
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
