"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from itertools import pairwise
from pathlib import Path

import pytest

from latebuf.simulator import LatenessDistribution, generate


def test_simulator_deterministic():
    a = generate(n_events=100, seed=42)
    b = generate(n_events=100, seed=42)
    assert a == b


def test_simulator_different_seeds_differ():
    a = generate(n_events=100, seed=1)
    b = generate(n_events=100, seed=2)
    assert a != b


def test_simulator_event_count():
    events = generate(n_events=50, seed=0)
    assert len(events) == 50


def test_simulator_ingest_monotonic():
    """ingest_time is monotonic non-decreasing across the stream."""
    events = generate(n_events=100, seed=0)
    for prev, curr in pairwise(events):
        assert curr.ingest_time >= prev.ingest_time


def test_simulator_heavy_tail_has_outliers():
    """HEAVY_TAIL distribution produces some events with high lateness."""
    events = generate(
        n_events=500,
        seed=0,
        distribution=LatenessDistribution.HEAVY_TAIL,
        max_lateness_seconds=30,
        p95_seconds=5,
    )
    latenesses = [(e.ingest_time - e.event_time).total_seconds() for e in events]
    # At least some events should be > p95 (i.e., in the heavy tail)
    assert max(latenesses) > 5


def test_simulator_bounded_caps_lateness():
    events = generate(
        n_events=500,
        seed=0,
        distribution=LatenessDistribution.BOUNDED,
        max_lateness_seconds=10,
    )
    latenesses = [(e.ingest_time - e.event_time).total_seconds() for e in events]
    assert max(latenesses) <= 10


def test_simulator_punctuation_marker_periodic():
    """Punctuation events appear at ``punctuation_every`` cadence."""
    events = generate(n_events=200, seed=0, punctuation_every=50)
    punct = [e for e in events if e.is_punctuation]
    assert len(punct) >= 3  # 200 / 50 = 4 punctuations


def test_simulator_rejects_invalid_args():
    with pytest.raises(ValueError):
        generate(n_events=-1)
    with pytest.raises(ValueError):
        generate(interval_seconds=0)
    with pytest.raises(ValueError):
        generate(max_lateness_seconds=-1)
    with pytest.raises(ValueError):
        generate(punctuation_every=0)


# ---------- CLI --------------------------------------------------------------


_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "latebuf.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    out = _run_cli("info")
    assert out.returncode == 0
    assert "late-arriving-data-buffer" in out.stdout


def test_cli_pipeline_simulate_run(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    out_path = tmp_path / "out.jsonl"
    r = _run_cli("simulate", "--events", "100", "--seed", "1", "--output", str(events_path))
    assert r.returncode == 0, r.stderr
    r = _run_cli(
        "run",
        "--input",
        str(events_path),
        "--allowed-lateness",
        "60",
        "--output",
        str(out_path),
        "--show",
    )
    assert r.returncode == 0, r.stderr
    assert out_path.exists()


def test_cli_run_exit_code_2_on_drops(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    _run_cli(
        "simulate",
        "--events",
        "200",
        "--seed",
        "1",
        "--max-lateness",
        "30",
        "--output",
        str(events_path),
    )
    # Tight watermark → some drops
    r = _run_cli("run", "--input", str(events_path), "--allowed-lateness", "1")
    assert r.returncode == 2


def test_cli_summary_outputs_json(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    _run_cli("simulate", "--events", "100", "--seed", "1", "--output", str(events_path))
    r = _run_cli("summary", "--input", str(events_path), "--allowed-lateness", "60")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert "n_accepted" in payload
    assert "drop_rate_pct" in payload


def test_cli_run_periodic_strategy(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    _run_cli("simulate", "--events", "100", "--seed", "1", "--output", str(events_path))
    r = _run_cli(
        "run",
        "--input",
        str(events_path),
        "--strategy",
        "PERIODIC",
        "--tick",
        "10",
        "--allowed-lateness",
        "60",
        "--show",
    )
    assert r.returncode == 0, r.stderr
