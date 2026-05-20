"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from cdc.simulator import generate


def test_generate_default() -> None:
    events = generate(n_customers=5, n_orders=10, seed=0)
    assert len(events) > 0


def test_generate_deterministic() -> None:
    a = generate(n_customers=5, n_orders=10, seed=42)
    b = generate(n_customers=5, n_orders=10, seed=42)
    assert a == b


def test_generate_includes_all_ops() -> None:
    from cdc.schema import Op

    events = generate(n_customers=5, n_orders=20, delete_fraction=0.5, seed=11)
    ops = {e.op for e in events}
    assert Op.CREATE in ops
    assert Op.UPDATE in ops
    assert Op.DELETE in ops


def test_generate_validates() -> None:
    with pytest.raises(ValueError, match="n_customers"):
        generate(n_customers=-1)
    with pytest.raises(ValueError, match="delete_fraction"):
        generate(delete_fraction=1.5)


def test_generate_zero_customers_or_orders() -> None:
    """Boundary: zero customers / orders produce empty or minimal output."""
    assert generate(n_customers=0, n_orders=10, seed=0) == []
    # n_customers=5, n_orders=0 → only customer INSERTs.
    events = generate(n_customers=5, n_orders=0, seed=0)
    assert len(events) == 5


def test_generate_position_strictly_increasing() -> None:
    events = generate(n_customers=3, n_orders=5, seed=0)
    for i in range(1, len(events)):
        assert events[i - 1].position < events[i].position


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cdc.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "change-data-capture" in r.stdout


def test_cli_simulate_and_replay(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    r = _run(
        "simulate",
        "--customers",
        "5",
        "--orders",
        "10",
        "--seed",
        "7",
        "--output",
        str(event_file),
    )
    assert r.returncode == 0, r.stderr
    assert event_file.exists()

    r = _run("replay", "--input", str(event_file))
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["n_rows"] > 0


def test_cli_compact(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    compacted_file = tmp_path / "compacted.jsonl"
    r = _run(
        "simulate",
        "--customers",
        "5",
        "--orders",
        "10",
        "--seed",
        "0",
        "--output",
        str(event_file),
    )
    assert r.returncode == 0

    r = _run(
        "compact",
        "--input",
        str(event_file),
        "--output",
        str(compacted_file),
    )
    assert r.returncode == 0, r.stderr
    assert compacted_file.exists()
    # Compaction should reduce event count.
    original = event_file.read_text().count("\n")
    compacted = compacted_file.read_text().count("\n")
    assert compacted <= original


def test_cli_diff(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    diff_file = tmp_path / "diffs.jsonl"
    _run(
        "simulate",
        "--customers",
        "5",
        "--orders",
        "10",
        "--seed",
        "0",
        "--output",
        str(event_file),
    )
    r = _run("diff", "--input", str(event_file), "--output", str(diff_file))
    assert r.returncode == 0, r.stderr
    assert diff_file.exists()


def test_cli_lineage(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    lineage_file = tmp_path / "lineage.jsonl"
    _run(
        "simulate",
        "--customers",
        "5",
        "--orders",
        "10",
        "--seed",
        "0",
        "--output",
        str(event_file),
    )
    r = _run(
        "lineage",
        "--input",
        str(event_file),
        "--output",
        str(lineage_file),
        "--show",
        "0",
    )
    assert r.returncode == 0, r.stderr
    assert lineage_file.exists()


def test_cli_replay_unordered(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    _run(
        "simulate",
        "--customers",
        "5",
        "--orders",
        "10",
        "--seed",
        "0",
        "--output",
        str(event_file),
    )
    r = _run("replay", "--input", str(event_file), "--unordered")
    assert r.returncode == 0
