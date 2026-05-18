"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hllpp.simulator import StreamPattern, generate

# ---------- simulator -------------------------------------------------------


def test_simulator_deterministic():
    a = generate(n=100, seed=42)
    b = generate(n=100, seed=42)
    assert a == b


def test_simulator_different_seeds_disjoint_for_unique():
    """UNIQUE values are seed-namespaced so disjoint streams produce disjoint sets."""
    a = set(generate(n=50, seed=1, pattern=StreamPattern.UNIQUE))
    b = set(generate(n=50, seed=2, pattern=StreamPattern.UNIQUE))
    assert a.isdisjoint(b)


def test_simulator_count_unique():
    out = generate(n=100, pattern=StreamPattern.UNIQUE, seed=0)
    assert len(out) == 100
    assert len(set(out)) == 100  # all distinct


def test_simulator_duplicated_has_repeats():
    out = generate(n=100, pattern=StreamPattern.DUPLICATED, duplication=10, seed=0)
    assert len(out) == 100
    assert len(set(out)) <= 15  # ~10 distinct (with some randomness)


def test_simulator_power_law_concentrated():
    """High-skew Zipf concentrates mass on a few values."""
    out = generate(n=1_000, pattern=StreamPattern.POWER_LAW, skew=2.0, seed=0)
    counts: dict[str, int] = {}
    for v in out:
        counts[v] = counts.get(v, 0) + 1
    # Sorted descending, top item should dominate
    sorted_counts = sorted(counts.values(), reverse=True)
    # Top-1 should be at least 20% of the stream when skew is 2.0
    assert sorted_counts[0] > 200


def test_simulator_rejects_invalid_args():
    with pytest.raises(ValueError):
        generate(n=-1)
    with pytest.raises(ValueError):
        generate(duplication=0)
    with pytest.raises(ValueError):
        generate(skew=-1.0)


# ---------- CLI --------------------------------------------------------------


_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "hllpp.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    r = _run_cli("info")
    assert r.returncode == 0
    assert "hyperloglog-cardinality" in r.stdout


def test_cli_full_pipeline(tmp_path: Path) -> None:
    values_path = tmp_path / "vals.txt"
    sketch_path = tmp_path / "sketch.json"
    r = _run_cli("simulate", "--n", "1000", "--seed", "1", "--output", str(values_path))
    assert r.returncode == 0
    r = _run_cli(
        "add", "--input", str(values_path), "--precision", "10", "--output", str(sketch_path)
    )
    assert r.returncode == 0
    r = _run_cli("estimate", "--input", str(sketch_path), "--json")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["precision"] == 10
    assert 900 <= payload["estimated_cardinality"] <= 1_100


def test_cli_summary_one_shot(tmp_path: Path) -> None:
    values_path = tmp_path / "vals.txt"
    _run_cli("simulate", "--n", "5000", "--seed", "1", "--output", str(values_path))
    r = _run_cli("summary", "--input", str(values_path), "--precision", "12")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert 4_700 <= payload["estimated_cardinality"] <= 5_300


def test_cli_merge_two_sketches(tmp_path: Path) -> None:
    a_vals = tmp_path / "a.txt"
    b_vals = tmp_path / "b.txt"
    a_skt = tmp_path / "a.json"
    b_skt = tmp_path / "b.json"
    merged = tmp_path / "merged.json"
    _run_cli("simulate", "--n", "5000", "--seed", "1", "--output", str(a_vals))
    _run_cli("simulate", "--n", "5000", "--seed", "2", "--output", str(b_vals))
    _run_cli("add", "--input", str(a_vals), "--output", str(a_skt))
    _run_cli("add", "--input", str(b_vals), "--output", str(b_skt))
    r = _run_cli("merge", str(a_skt), str(b_skt), "--output", str(merged))
    assert r.returncode == 0
    r = _run_cli("estimate", "--input", str(merged), "--json")
    payload = json.loads(r.stdout)
    # Union of 5k+5k disjoint should be ~10k
    assert 9_500 <= payload["estimated_cardinality"] <= 10_500
