"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bloom.simulator import mixed_stream, uniform_stream, zipf_stream

# ---------- simulator -------------------------------------------------------


def test_uniform_stream_size() -> None:
    assert len(uniform_stream(100)) == 100


def test_uniform_stream_deterministic() -> None:
    assert uniform_stream(50, seed=7) == uniform_stream(50, seed=7)


def test_uniform_stream_zero() -> None:
    assert uniform_stream(0) == []


def test_uniform_stream_validates() -> None:
    with pytest.raises(ValueError):
        uniform_stream(-1)


def test_zipf_stream_basic() -> None:
    s = zipf_stream(200, vocab_size=100, alpha=1.5, seed=0)
    assert len(s) == 200
    # Zipf is heavy-headed: vocabulary used should be < 100.
    assert len(set(s)) < 100


def test_zipf_stream_deterministic() -> None:
    a = zipf_stream(100, seed=3)
    b = zipf_stream(100, seed=3)
    assert a == b


def test_zipf_stream_validates() -> None:
    with pytest.raises(ValueError, match="alpha"):
        zipf_stream(100, alpha=1.0)
    with pytest.raises(ValueError, match="vocab_size"):
        zipf_stream(100, vocab_size=0)


def test_mixed_stream_disjoint() -> None:
    pos, neg = mixed_stream(100, 100, seed=0)
    assert len(pos) == 100
    assert len(neg) == 100
    # Different prefixes guarantee disjointness.
    assert set(pos).isdisjoint(set(neg))


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bloom.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "bloom-filter" in r.stdout


def test_cli_size() -> None:
    r = _run("size", "--capacity", "1000", "--fpr", "0.01")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["capacity"] == 1000
    assert payload["target_fpr"] == 0.01
    assert payload["size_bits"] > 9_000
    assert 6 <= payload["n_hashes"] <= 8


def test_cli_build_then_check(tmp_path: Path) -> None:
    values = tmp_path / "values.txt"
    values.write_text("\n".join(f"v-{i}" for i in range(100)) + "\n")
    filter_file = tmp_path / "filter.jsonl"

    r = _run(
        "build",
        "--input",
        str(values),
        "--capacity",
        "100",
        "--fpr",
        "0.01",
        "--output",
        str(filter_file),
    )
    assert r.returncode == 0
    assert filter_file.exists()

    # Query with same values: 100% hit.
    r = _run(
        "check",
        "--filter",
        str(filter_file),
        "--input",
        str(values),
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["n_hits"] == 100
    assert payload["hit_rate"] == 1.0


def test_cli_bench() -> None:
    r = _run(
        "bench",
        "--n-positive",
        "1000",
        "--n-negative",
        "5000",
        "--fpr",
        "0.01",
        "--seed",
        "7",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["true_positive_rate"] == 1.0  # no false negatives
    # Observed FPR within 5× of expected (small-sample noise).
    assert payload["observed_fpr"] < 0.05
