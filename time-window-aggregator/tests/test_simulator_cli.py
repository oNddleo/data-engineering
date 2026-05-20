"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from windows.simulator import bursty_stream, uniform_stream


def test_uniform_stream_size() -> None:
    events = uniform_stream(n_keys=5, n_events_per_key=10, seed=0)
    assert len(events) == 50


def test_uniform_stream_deterministic() -> None:
    a = uniform_stream(n_keys=3, n_events_per_key=5, seed=42)
    b = uniform_stream(n_keys=3, n_events_per_key=5, seed=42)
    assert a == b


def test_uniform_stream_validates() -> None:
    with pytest.raises(ValueError):
        uniform_stream(n_keys=-1)
    with pytest.raises(ValueError):
        uniform_stream(interval_ms=0)


def test_bursty_stream_structure() -> None:
    events = bursty_stream(
        n_keys=2,
        n_bursts=3,
        events_per_burst=10,
        seed=0,
    )
    assert len(events) == 2 * 3 * 10


def test_bursty_stream_deterministic() -> None:
    a = bursty_stream(n_keys=2, n_bursts=2, events_per_burst=5, seed=7)
    b = bursty_stream(n_keys=2, n_bursts=2, events_per_burst=5, seed=7)
    assert a == b


def test_bursty_stream_validates() -> None:
    with pytest.raises(ValueError):
        bursty_stream(burst_duration_ms=0)


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "windows.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "time-window-aggregator" in r.stdout


def test_cli_end_to_end_tumbling(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    agg_file = tmp_path / "aggs.jsonl"

    r = _run(
        "simulate",
        "--keys",
        "3",
        "--events",
        "20",
        "--interval-ms",
        "100",
        "--seed",
        "7",
        "--output",
        str(event_file),
    )
    assert r.returncode == 0, r.stderr
    assert event_file.exists()

    r = _run(
        "tumbling",
        "--input",
        str(event_file),
        "--width-ms",
        "500",
        "--output",
        str(agg_file),
    )
    assert r.returncode == 0, r.stderr
    assert agg_file.exists()


def test_cli_sliding(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    agg_file = tmp_path / "aggs.jsonl"
    assert (
        _run(
            "simulate",
            "--keys",
            "2",
            "--events",
            "10",
            "--interval-ms",
            "100",
            "--seed",
            "0",
            "--output",
            str(event_file),
        ).returncode
        == 0
    )
    r = _run(
        "sliding",
        "--input",
        str(event_file),
        "--width-ms",
        "500",
        "--stride-ms",
        "100",
        "--output",
        str(agg_file),
    )
    assert r.returncode == 0, r.stderr


def test_cli_session(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    assert (
        _run(
            "simulate",
            "--keys",
            "2",
            "--bursty",
            "--bursts",
            "3",
            "--burst-size",
            "10",
            "--seed",
            "0",
            "--output",
            str(event_file),
        ).returncode
        == 0
    )
    r = _run(
        "session",
        "--input",
        str(event_file),
        "--timeout-ms",
        "120000",
    )
    assert r.returncode == 0, r.stderr


def test_cli_summary(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    agg_file = tmp_path / "aggs.jsonl"
    assert (
        _run(
            "simulate",
            "--keys",
            "3",
            "--events",
            "20",
            "--seed",
            "0",
            "--output",
            str(event_file),
        ).returncode
        == 0
    )
    assert (
        _run(
            "tumbling",
            "--input",
            str(event_file),
            "--width-ms",
            "500",
            "--output",
            str(agg_file),
        ).returncode
        == 0
    )
    r = _run("summary", "--input", str(agg_file))
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["n_aggregates"] > 0
