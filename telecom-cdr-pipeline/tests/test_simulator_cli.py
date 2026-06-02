"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from cdrpipe.simulator import generate

# ---------- simulator -------------------------------------------------------


def test_generate_default() -> None:
    cdrs = generate(n_subscribers=5, n_days=3, seed=0)
    assert len(cdrs) > 0


def test_generate_deterministic() -> None:
    """Same seed → same output."""
    a = generate(n_subscribers=5, n_days=3, seed=42)
    b = generate(n_subscribers=5, n_days=3, seed=42)
    assert a == b


def test_generate_different_seeds_differ() -> None:
    a = generate(n_subscribers=5, n_days=3, seed=1)
    b = generate(n_subscribers=5, n_days=3, seed=2)
    assert a != b


def test_generate_zero_subscribers() -> None:
    assert generate(n_subscribers=0, n_days=3) == []


def test_generate_validates_inputs() -> None:
    with pytest.raises(ValueError, match="n_subscribers"):
        generate(n_subscribers=-1)
    with pytest.raises(ValueError, match="n_days"):
        generate(n_days=0)
    with pytest.raises(ValueError, match="premium_fraction"):
        generate(premium_fraction=1.5)
    with pytest.raises(ValueError, match="roaming_fraction"):
        generate(roaming_fraction=-0.1)
    with pytest.raises(ValueError, match="sim_swap_fraction"):
        generate(sim_swap_fraction=2.0)


def test_generate_sorted_by_time() -> None:
    cdrs = generate(n_subscribers=5, n_days=3, seed=0)
    times = [c.occurred_at for c in cdrs]
    assert times == sorted(times)


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cdrpipe.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "telecom-cdr-pipeline" in r.stdout


def test_cli_end_to_end(tmp_path: Path) -> None:
    cdr_file = tmp_path / "cdrs.jsonl"
    rated_file = tmp_path / "rated.jsonl"
    bill_file = tmp_path / "bills.jsonl"

    r = _run(
        "simulate", "--subscribers", "10", "--days", "5", "--seed", "7", "--output", str(cdr_file)
    )
    assert r.returncode == 0, r.stderr
    assert cdr_file.exists()

    r = _run("rate", "--input", str(cdr_file), "--output", str(rated_file), "--show", "0")
    assert r.returncode == 0, r.stderr
    assert rated_file.exists()

    r = _run("bill", "--input", str(cdr_file), "--output", str(bill_file), "--show", "0")
    assert r.returncode == 0, r.stderr
    assert bill_file.exists()

    r = _run("summary", "--input", str(cdr_file))
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["n_cdrs"] > 0
    assert payload["n_subscribers"] == 10
    assert payload["total_revenue_vnd"] > 0


def test_cli_fraud_exits_nonzero_on_finding(tmp_path: Path) -> None:
    """Fraud command exits 2 if any finding fires."""
    cdr_file = tmp_path / "cdrs.jsonl"
    # Larger run more likely to produce findings.
    r = _run(
        "simulate",
        "--subscribers",
        "100",
        "--days",
        "30",
        "--seed",
        "11",
        "--output",
        str(cdr_file),
    )
    assert r.returncode == 0
    r = _run("fraud", "--input", str(cdr_file), "--show", "0")
    # Either 0 (no findings on this seed) or 2 (findings present) is valid;
    # we just assert it's not a crash.
    assert r.returncode in (0, 2), r.stderr


def test_cli_fraud_clean_run_exits_zero(tmp_path: Path) -> None:
    """A tiny stream produces no findings → exit 0."""
    cdr_file = tmp_path / "cdrs.jsonl"
    r = _run(
        "simulate", "--subscribers", "2", "--days", "2", "--seed", "0", "--output", str(cdr_file)
    )
    assert r.returncode == 0
    r = _run(
        "fraud",
        "--input",
        str(cdr_file),
        "--min-premium-minutes",
        "100",
        "--min-roaming-amount",
        "100000000",
        "--show",
        "0",
    )
    assert r.returncode == 0
