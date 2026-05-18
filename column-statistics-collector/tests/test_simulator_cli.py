"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from colstats.simulator import (
    NumericShape,
    generate_categorical,
    generate_date,
    generate_numeric,
    generate_string,
)


def test_numeric_simulator_deterministic():
    a = generate_numeric(n=100, seed=42)
    b = generate_numeric(n=100, seed=42)
    assert a == b


def test_numeric_simulator_count():
    out = generate_numeric(n=50, seed=0)
    assert len(out) == 50


def test_numeric_simulator_respects_null_fraction():
    out = generate_numeric(n=10_000, null_fraction=0.5, seed=0)
    nulls = sum(1 for v in out if v == "")
    # ~50% with some slack
    assert 4_500 <= nulls <= 5_500


def test_numeric_simulator_uniform_in_range():
    out = generate_numeric(n=100, shape=NumericShape.UNIFORM, low=0.0, high=100.0, seed=0)
    floats = [float(v) for v in out if v]
    assert all(0 <= x <= 100 for x in floats)


def test_categorical_simulator_zipf():
    """High skew → first category dominates."""
    out = generate_categorical(n=1_000, n_categories=5, skew=2.0, seed=0)
    counts: dict[str, int] = {}
    for v in out:
        counts[v] = counts.get(v, 0) + 1
    assert counts.get("cat_0", 0) > counts.get("cat_4", 0)


def test_categorical_simulator_uniform_when_skew_zero():
    """Skew=0 → roughly uniform distribution."""
    out = generate_categorical(n=10_000, n_categories=5, skew=0.0, seed=0)
    counts: dict[str, int] = {}
    for v in out:
        counts[v] = counts.get(v, 0) + 1
    # Each category should be ~ 20% (with slack)
    for c in counts.values():
        assert 1_700 <= c <= 2_300


def test_string_simulator_length():
    out = generate_string(n=10, length=8, seed=0)
    for v in out:
        if v:
            assert len(v) == 8


def test_date_simulator_in_range():
    out = generate_date(n=100, span_days=30, seed=0)
    nonempty = [v for v in out if v]
    # All dates should be parseable.
    from datetime import date

    for v in nonempty:
        assert isinstance(date.fromisoformat(v), date)


def test_simulator_rejects_invalid_args():
    with pytest.raises(ValueError):
        generate_numeric(n=-1)
    with pytest.raises(ValueError):
        generate_numeric(null_fraction=1.5)
    with pytest.raises(ValueError):
        generate_categorical(n_categories=0)
    with pytest.raises(ValueError):
        generate_string(length=0)
    with pytest.raises(ValueError):
        generate_date(span_days=0)


# ---------- CLI --------------------------------------------------------------


_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "colstats.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    r = _run_cli("info")
    assert r.returncode == 0
    assert "column-statistics-collector" in r.stdout


def test_cli_simulate_profile_pipeline(tmp_path: Path) -> None:
    values_path = tmp_path / "col.txt"
    profile_path = tmp_path / "prof.json"
    r = _run_cli(
        "simulate",
        "--kind",
        "NUMERIC",
        "--rows",
        "100",
        "--seed",
        "1",
        "--output",
        str(values_path),
    )
    assert r.returncode == 0, r.stderr
    r = _run_cli(
        "profile",
        "--input",
        str(values_path),
        "--kind",
        "NUMERIC",
        "--output",
        str(profile_path),
        "--show",
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "NUMERIC"
    assert payload["n_rows"] == 100


def test_cli_drift_detects_shift(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.txt"
    drift_path = tmp_path / "drift.txt"
    profile_path = tmp_path / "prof.json"

    _run_cli(
        "simulate",
        "--kind",
        "NUMERIC",
        "--shape",
        "GAUSSIAN",
        "--mean",
        "100",
        "--std",
        "20",
        "--rows",
        "1000",
        "--seed",
        "1",
        "--output",
        str(baseline_path),
    )
    _run_cli(
        "simulate",
        "--kind",
        "NUMERIC",
        "--shape",
        "GAUSSIAN",
        "--mean",
        "200",
        "--std",
        "20",
        "--rows",
        "1000",
        "--seed",
        "1",
        "--output",
        str(drift_path),
    )
    _run_cli(
        "profile", "--input", str(baseline_path), "--kind", "NUMERIC", "--output", str(profile_path)
    )

    r = _run_cli("drift", "--baseline", str(profile_path), "--compared-values", str(drift_path))
    assert r.returncode == 2  # significant drift → exit 2
    assert "significant" in r.stdout


def test_cli_drift_stable_when_same(tmp_path: Path) -> None:
    values_path = tmp_path / "col.txt"
    profile_path = tmp_path / "prof.json"
    _run_cli(
        "simulate",
        "--kind",
        "NUMERIC",
        "--rows",
        "1000",
        "--seed",
        "1",
        "--output",
        str(values_path),
    )
    _run_cli(
        "profile", "--input", str(values_path), "--kind", "NUMERIC", "--output", str(profile_path)
    )
    r = _run_cli("drift", "--baseline", str(profile_path), "--compared-values", str(values_path))
    assert r.returncode == 0
    assert "stable" in r.stdout


def test_cli_summary_outputs_json(tmp_path: Path) -> None:
    values_path = tmp_path / "col.txt"
    _run_cli(
        "simulate",
        "--kind",
        "CATEGORICAL",
        "--rows",
        "100",
        "--seed",
        "1",
        "--output",
        str(values_path),
    )
    r = _run_cli("summary", "--input", str(values_path), "--kind", "CATEGORICAL")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["kind"] == "CATEGORICAL"
    assert payload["n_rows"] == 100
