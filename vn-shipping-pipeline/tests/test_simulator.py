"""Simulator + CLI tests."""

from __future__ import annotations

import json
import subprocess
import sys

from vnship.simulator import generate, summarise


def test_generate_count() -> None:
    assert len(generate(n=50, seed=0)) == 50


def test_generate_deterministic() -> None:
    assert generate(n=100, seed=7) == generate(n=100, seed=7)


def test_generate_bad_n_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        generate(n=0)


def test_summarise_empty() -> None:
    s = summarise([])
    assert s.n_shipments == 0
    assert s.avg_fee_vnd == 0.0


def test_summarise_counts() -> None:
    results = generate(n=200, seed=42)
    s = summarise(results)
    assert s.n_shipments == 200
    assert sum(s.carrier_counts.values()) == 200
    assert s.total_fee_vnd == sum(r.total_fee_vnd for r in results)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vnship.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_carriers() -> None:
    r = _run("carriers")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "GHN" in data["carriers"]


def test_cli_price() -> None:
    r = _run(
        "price",
        "--carrier",
        "GHN",
        "--service",
        "STANDARD",
        "--zone",
        "INNER_CITY",
        "--weight-g",
        "500",
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["base_fee_vnd"] == 22_000
    assert data["total_fee_vnd"] > 0


def test_cli_simulate() -> None:
    r = _run("simulate", "--n", "50", "--seed", "0")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["n_shipments"] == 50
    assert data["total_fee_vnd"] > 0
