"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from reservoir.simulator import uniform_stream, weighted_pairs, zipf_stream

# ---------- simulator -------------------------------------------------------


def test_uniform_stream_size() -> None:
    assert len(uniform_stream(100)) == 100


def test_uniform_stream_unique() -> None:
    """uniform_stream should produce distinct tokens."""
    assert len(set(uniform_stream(100))) == 100


def test_uniform_stream_rejects_negative() -> None:
    with pytest.raises(ValueError, match="n"):
        uniform_stream(-1)


def test_zipf_stream_size() -> None:
    assert len(zipf_stream(50)) == 50


def test_zipf_stream_skewed() -> None:
    """Zipf is heavy-headed: vocabulary used should be << total."""
    s = zipf_stream(200, vocab_size=100, alpha=1.5, seed=0)
    assert len(set(s)) < 100


def test_zipf_stream_rejects_bad_alpha() -> None:
    with pytest.raises(ValueError, match="alpha"):
        zipf_stream(50, alpha=1.0)


def test_weighted_pairs_uniform() -> None:
    pairs = weighted_pairs(50, distribution="uniform")
    assert len(pairs) == 50
    for _, w in pairs:
        assert 1.0 <= w <= 10.0


def test_weighted_pairs_binary() -> None:
    pairs = weighted_pairs(200, distribution="binary", seed=0)
    # Weights are either 1 or 100.
    weights = {w for _, w in pairs}
    assert weights == {1.0, 100.0}


def test_weighted_pairs_unknown_distribution() -> None:
    with pytest.raises(ValueError, match="distribution"):
        weighted_pairs(10, distribution="???")


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "reservoir.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "reservoir-sampling" in r.stdout


def test_cli_sample_r(tmp_path: Path) -> None:
    values = tmp_path / "values.txt"
    values.write_text("\n".join(f"v-{i}" for i in range(100)) + "\n")
    out_file = tmp_path / "reservoir.jsonl"

    r = _run(
        "sample",
        "--input",
        str(values),
        "--k",
        "10",
        "--algorithm",
        "R",
        "--seed",
        "7",
        "--output",
        str(out_file),
    )
    assert r.returncode == 0, r.stderr
    assert out_file.exists()
    payload = json.loads(out_file.read_text().strip())
    assert payload["capacity"] == 10
    assert payload["n_seen"] == 100


def test_cli_sample_l(tmp_path: Path) -> None:
    values = tmp_path / "values.txt"
    values.write_text("\n".join(f"v-{i}" for i in range(100)) + "\n")
    out_file = tmp_path / "reservoir.jsonl"

    r = _run(
        "sample",
        "--input",
        str(values),
        "--k",
        "10",
        "--algorithm",
        "L",
        "--seed",
        "7",
        "--output",
        str(out_file),
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(out_file.read_text().strip())
    assert len(payload["items"]) == 10


def test_cli_merge(tmp_path: Path) -> None:
    """Two saved reservoirs merge into one of the same capacity."""
    a_file = tmp_path / "a.jsonl"
    b_file = tmp_path / "b.jsonl"
    merged_file = tmp_path / "merged.jsonl"

    values_a = tmp_path / "vals_a.txt"
    values_a.write_text("\n".join(f"a-{i}" for i in range(50)) + "\n")
    values_b = tmp_path / "vals_b.txt"
    values_b.write_text("\n".join(f"b-{i}" for i in range(50)) + "\n")

    assert (
        _run(
            "sample",
            "--input",
            str(values_a),
            "--k",
            "10",
            "--seed",
            "1",
            "--output",
            str(a_file),
        ).returncode
        == 0
    )
    assert (
        _run(
            "sample",
            "--input",
            str(values_b),
            "--k",
            "10",
            "--seed",
            "2",
            "--output",
            str(b_file),
        ).returncode
        == 0
    )

    r = _run(
        "merge", "--a", str(a_file), "--b", str(b_file), "--seed", "0", "--output", str(merged_file)
    )
    assert r.returncode == 0
    merged = json.loads(merged_file.read_text().strip())
    assert merged["n_seen"] == 100
    assert merged["capacity"] == 10


def test_cli_bench_r() -> None:
    r = _run(
        "bench",
        "--algorithm",
        "R",
        "--n",
        "100",
        "--k",
        "10",
        "--trials",
        "100",
        "--seed",
        "0",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["expected_picks_per_item"] == 10.0
    assert payload["distinct_items_picked"] == 100


def test_cli_bench_l() -> None:
    r = _run(
        "bench",
        "--algorithm",
        "L",
        "--n",
        "100",
        "--k",
        "10",
        "--trials",
        "100",
        "--seed",
        "0",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["distinct_items_picked"] == 100
