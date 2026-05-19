"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cms.simulator import StreamPattern, generate


def test_simulator_deterministic():
    a = generate(n=200, seed=42)
    b = generate(n=200, seed=42)
    assert a == b


def test_simulator_different_seeds_namespace_disjoint():
    a = set(generate(n=100, pattern=StreamPattern.UNIFORM, seed=1))
    b = set(generate(n=100, pattern=StreamPattern.UNIFORM, seed=2))
    assert a.isdisjoint(b)


def test_simulator_count_matches_n():
    out = generate(n=500, seed=0)
    assert len(out) == 500


def test_simulator_zipf_concentrates():
    out = generate(n=10_000, vocab_size=1_000, pattern=StreamPattern.ZIPF, skew=2.0, seed=0)
    counts: dict[str, int] = {}
    for v in out:
        counts[v] = counts.get(v, 0) + 1
    sorted_counts = sorted(counts.values(), reverse=True)
    # Top-1 should dominate when skew is high.
    assert sorted_counts[0] > 500


def test_simulator_heavy_hitters_pattern():
    out = generate(
        n=10_000,
        vocab_size=1_000,
        pattern=StreamPattern.HEAVY_HITTERS,
        n_heavy=5,
        heavy_fraction=0.7,
        seed=0,
    )
    counts: dict[str, int] = {}
    for v in out:
        counts[v] = counts.get(v, 0) + 1
    # The 5 heavy values should hold ~70% of total mass.
    sorted_counts = sorted(counts.values(), reverse=True)
    top_5_mass = sum(sorted_counts[:5])
    assert 5_500 <= top_5_mass <= 8_000


def test_simulator_rejects_invalid_args():
    with pytest.raises(ValueError):
        generate(n=-1)
    with pytest.raises(ValueError):
        generate(vocab_size=0)
    with pytest.raises(ValueError):
        generate(skew=-1)
    with pytest.raises(ValueError):
        generate(heavy_fraction=1.5)


# ---------- CLI -------------------------------------------------------------


_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "cms.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    r = _run_cli("info")
    assert r.returncode == 0
    assert "count-min-sketch" in r.stdout


def test_cli_full_pipeline(tmp_path: Path) -> None:
    values_path = tmp_path / "vals.txt"
    sketch_path = tmp_path / "sketch.json"
    r = _run_cli("simulate", "--n", "1000", "--seed", "1", "--output", str(values_path))
    assert r.returncode == 0
    r = _run_cli("add", "--input", str(values_path), "--output", str(sketch_path))
    assert r.returncode == 0
    r = _run_cli("estimate", "--input", str(sketch_path), "--value", "s1_v_00000000")
    assert r.returncode == 0
    assert "estimated count" in r.stdout


def test_cli_heavy_finds_top_k(tmp_path: Path) -> None:
    """Top-K extraction surfaces the heavy hitters."""
    values_path = tmp_path / "vals.txt"
    _run_cli(
        "simulate",
        "--n",
        "5000",
        "--vocab",
        "50",
        "--pattern",
        "HEAVY_HITTERS",
        "--n-heavy",
        "3",
        "--heavy-fraction",
        "0.8",
        "--seed",
        "1",
        "--output",
        str(values_path),
    )
    r = _run_cli("heavy", "--input", str(values_path), "--k", "5", "--json")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    # Top 3 by frequency should each have a meaningful fraction.
    assert payload[0]["fraction_of_total"] > 0.10
    assert payload[1]["fraction_of_total"] > 0.10
    assert payload[2]["fraction_of_total"] > 0.10


def test_cli_summary_outputs_json(tmp_path: Path) -> None:
    values_path = tmp_path / "vals.txt"
    _run_cli("simulate", "--n", "1000", "--seed", "1", "--output", str(values_path))
    r = _run_cli("summary", "--input", str(values_path))
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["total_count"] == 1_000
    assert payload["max_counter"] > 0


def test_cli_merge_combines_sketches(tmp_path: Path) -> None:
    a_vals = tmp_path / "a.txt"
    b_vals = tmp_path / "b.txt"
    a_skt = tmp_path / "a.json"
    b_skt = tmp_path / "b.json"
    merged = tmp_path / "merged.json"
    _run_cli("simulate", "--n", "500", "--seed", "1", "--output", str(a_vals))
    _run_cli("simulate", "--n", "500", "--seed", "2", "--output", str(b_vals))
    _run_cli("add", "--input", str(a_vals), "--output", str(a_skt))
    _run_cli("add", "--input", str(b_vals), "--output", str(b_skt))
    r = _run_cli("merge", str(a_skt), str(b_skt), "--output", str(merged))
    assert r.returncode == 0
    r = _run_cli("summary", "--input", str(a_vals))
    assert r.returncode == 0
