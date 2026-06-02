"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from csvinf.simulator import generate


def test_simulator_deterministic():
    a = generate(n_rows=30, seed=42)
    b = generate(n_rows=30, seed=42)
    assert a == b


def test_simulator_different_seeds():
    a = generate(n_rows=30, seed=1)
    b = generate(n_rows=30, seed=2)
    assert a != b


def test_simulator_has_header():
    text = generate(n_rows=10, seed=0)
    first = text.splitlines()[0]
    assert (
        first == "order_id,customer_name,email,amount_vnd,qty,is_paid,created_date,signed_at,note"
    )


def test_simulator_row_count():
    text = generate(n_rows=50, seed=0)
    # +1 for header
    assert len(text.splitlines()) == 51


def test_simulator_rejects_invalid_null_fraction():
    with pytest.raises(ValueError):
        generate(null_fraction=-0.1)
    with pytest.raises(ValueError):
        generate(null_fraction=1.5)


def test_simulator_rejects_negative_rows():
    with pytest.raises(ValueError):
        generate(n_rows=-1)


def test_simulator_custom_delimiter():
    text = generate(n_rows=5, delimiter=";", seed=0)
    assert ";" in text.splitlines()[0]
    assert "," not in text.splitlines()[0]


# ---------- CLI --------------------------------------------------------------


_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "csvinf.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    out = _run_cli("info")
    assert out.returncode == 0
    assert "csv-schema-inference-toolkit" in out.stdout


def test_cli_pipeline_simulate_infer_emit(tmp_path: Path) -> None:
    csv_path = tmp_path / "orders.csv"
    schema_path = tmp_path / "schema.json"
    avro_path = tmp_path / "out.avsc"

    r = _run_cli("simulate", "--rows", "20", "--seed", "1", "--output", str(csv_path))
    assert r.returncode == 0, r.stderr

    r = _run_cli("infer", "--input", str(csv_path), "--output", str(schema_path), "--show")
    assert r.returncode == 0, r.stderr
    assert schema_path.exists()
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    assert payload["n_rows_scanned"] == 20

    r = _run_cli(
        "emit",
        "--input",
        str(csv_path),
        "--format",
        "avro",
        "--name",
        "Order",
        "--output",
        str(avro_path),
    )
    assert r.returncode == 0, r.stderr
    avro = json.loads(avro_path.read_text(encoding="utf-8"))
    assert avro["type"] == "record"
    assert avro["name"] == "Order"


def test_cli_emit_dataclass(tmp_path: Path) -> None:
    csv_path = tmp_path / "orders.csv"
    _run_cli("simulate", "--rows", "10", "--seed", "1", "--output", str(csv_path))
    r = _run_cli("emit", "--input", str(csv_path), "--format", "dataclass", "--name", "Order")
    assert r.returncode == 0, r.stderr
    assert "class Order:" in r.stdout
    assert "@dataclass(frozen=True, slots=True)" in r.stdout


def test_cli_emit_json_schema(tmp_path: Path) -> None:
    csv_path = tmp_path / "orders.csv"
    _run_cli("simulate", "--rows", "10", "--seed", "1", "--output", str(csv_path))
    r = _run_cli("emit", "--input", str(csv_path), "--format", "json-schema", "--name", "Order")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["title"] == "Order"
    assert payload["type"] == "object"


def test_cli_summary(tmp_path: Path) -> None:
    csv_path = tmp_path / "orders.csv"
    _run_cli("simulate", "--rows", "20", "--seed", "1", "--output", str(csv_path))
    r = _run_cli("summary", "--input", str(csv_path))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["n_columns"] == 9
    assert "INT" in payload["columns_by_type"]
