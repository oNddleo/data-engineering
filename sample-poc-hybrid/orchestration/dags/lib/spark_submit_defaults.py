"""Shared helper used by every DAG to invoke spark-submit on spark-master.

Airflow 3.0 runs in its own container; the bind-mounted `/var/run/docker.sock`
lets us `docker exec` into the existing spark-master container instead of
spinning up a side-car container per task. This avoids:
- Re-downloading the spark image per task.
- Mismatched `spark-defaults.conf` between the executor and the submit env.

`spark_submit_in_master(script, config)` returns a list[str] suitable for
`subprocess.run(check=True)` inside an `@task` body.

Module name uses snake_case because Airflow's DAG processor imports it
through `importlib`, which cannot resolve a hyphenated identifier.
"""

from __future__ import annotations

import os
from typing import Sequence

SPARK_MASTER_CONTAINER = os.environ.get(
    "SPARK_MASTER_CONTAINER",
    "hybrid-spark-master-1",
)
SPARK_MASTER_URL = os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077")
SPARK_SUBMIT = "/opt/bitnami/spark/bin/spark-submit"
PIPELINE_DIR = "/opt/hybrid/pipeline"


def spark_submit_in_master(
    script: str,
    config: str | None = None,
    *,
    app_name: str | None = None,
    extra_args: Sequence[str] | None = None,
) -> list[str]:
    """Build the docker exec + spark-submit command line.

    `script` is the .py filename inside `pipeline/spark_jobs/`.
    `config` is the .yaml filename inside `pipeline/conf/` (omit for jobs
    that take their config from env).
    """
    cmd: list[str] = [
        "docker", "exec", SPARK_MASTER_CONTAINER,
        SPARK_SUBMIT,
        "--master", SPARK_MASTER_URL,
    ]
    if app_name:
        cmd += ["--name", app_name]
    cmd.append(f"{PIPELINE_DIR}/spark_jobs/{script}")
    if config:
        cmd += ["--config", f"{PIPELINE_DIR}/conf/{config}"]
    if extra_args:
        cmd += list(extra_args)
    return cmd
