"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tdigest.simulator import (
    exact_quantile,
    gaussian_stream,
    lognormal_stream,
    pareto_stream,
    uniform_stream,
)

# ---------- simulator -------------------------------------------------------


def test_uniform_stream_size() -> None:
    assert len(uniform_stream(100)) == 100


def test_uniform_deterministic() -> None:
    assert uniform_stream(50, seed=7) == uniform_stream(50, seed=7)


def test_gaussian_stream_size() -> None:
    assert len(gaussian_stream(100)) == 100


def test_gaussian_rejects_bad_sigma() -> None:
    with pytest.raises(ValueError, match="sigma"):
        gaussian_stream(10, sigma=0.0)


def test_lognormal_positive() -> None:
    """exp(N) is always positive."""
    vals = lognormal_stream(1000, seed=0)
    assert all(v > 0 for v in vals)


def test_pareto_at_least_one() -> None:
    """Pareto Type I with scale 1 has support [1, ∞)."""
    vals = pareto_stream(1000, seed=0)
    assert all(v >= 1.0 for v in vals)


def test_pareto_rejects_bad_alpha() -> None:
    with pytest.raises(ValueError, match="alpha"):
        pareto_stream(10, alpha=0.0)


def test_exact_quantile_endpoints() -> None:
    s = [3.0, 1.0, 2.0]
    assert exact_quantile(s, 0.0) == 1.0
    assert exact_quantile(s, 1.0) == 3.0


def test_exact_quantile_interpolates() -> None:
    s = [0.0, 1.0]
    assert exact_quantile(s, 0.5) == 0.5


def test_exact_quantile_rejects_empty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        exact_quantile([], 0.5)


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tdigest.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "t-digest" in r.stdout


def test_cli_build_quantile_cdf(tmp_path: Path) -> None:
    values = tmp_path / "values.txt"
    values.write_text("\n".join(str(i) for i in range(1000)) + "\n")
    digest_file = tmp_path / "digest.jsonl"

    r = _run(
        "build",
        "--input",
        str(values),
        "--compression",
        "100",
        "--output",
        str(digest_file),
    )
    assert r.returncode == 0, r.stderr
    assert digest_file.exists()

    r = _run(
        "quantile",
        "--input",
        str(digest_file),
        "--q",
        "0.1",
        "0.5",
        "0.9",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    # 0..999 → p10 ≈ 99, p50 ≈ 499, p90 ≈ 899.
    assert 70 <= payload["q0.1"] <= 130
    assert 470 <= payload["q0.5"] <= 530
    assert 870 <= payload["q0.9"] <= 930

    r = _run("cdf", "--input", str(digest_file), "--value", "500")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert 0.45 <= payload["cdf"] <= 0.55


def test_cli_bench_runs() -> None:
    r = _run(
        "bench",
        "--dist",
        "gaussian",
        "--n",
        "5000",
        "--compression",
        "100",
        "--seed",
        "3",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["n_samples"] == 5000
    assert payload["distribution"] == "gaussian"
    # Median should be close to 0 (gaussian default mu=0).
    median_row = next(r for r in payload["quantiles"] if r["q"] == 0.5)
    assert abs(median_row["estimate"]) < 0.1
