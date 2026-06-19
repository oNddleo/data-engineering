"""SparkSession factory used by all spark_jobs entry scripts.

The defaults shipped in `infra/spark/spark-defaults.conf` already wire up
Delta 4.0 + Hive Metastore + S3a + deletion vectors. This helper only adds
per-app overrides (app name, graceful shutdown for streaming) and stays
thin so unit tests can swap it out.
"""

from __future__ import annotations

from pyspark.sql import SparkSession


def build_streaming_session(
    app_name: str,
    *,
    stop_gracefully_on_shutdown: bool = True,
) -> SparkSession:
    """Return a SparkSession with the bronze-stream-friendly defaults applied.

    `spark.streaming.stopGracefullyOnShutdown=true` lets SIGTERM drain the
    current micro-batch before exiting; combined with checkpointing this is
    what makes restart-from-checkpoint at-least-once delivery work.
    """
    builder = SparkSession.builder.appName(app_name).enableHiveSupport()
    if stop_gracefully_on_shutdown:
        builder = builder.config("spark.streaming.stopGracefullyOnShutdown", "true")
    return builder.getOrCreate()
