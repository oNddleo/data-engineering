"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vnstock.simulator import generate


def test_generate_default() -> None:
    bars = generate(n_tickers=5, n_days=10, seed=0)
    assert len(bars) > 0


def test_generate_deterministic() -> None:
    a = generate(n_tickers=5, n_days=10, seed=42)
    b = generate(n_tickers=5, n_days=10, seed=42)
    assert a == b


def test_generate_skips_weekends() -> None:
    """No bars on weekend days."""
    bars = generate(n_tickers=3, n_days=14, seed=0)
    for b in bars:
        assert b.date.weekday() < 5


def test_generate_validates() -> None:
    with pytest.raises(ValueError, match="n_tickers"):
        generate(n_tickers=-1)
    with pytest.raises(ValueError, match="n_days"):
        generate(n_days=0)
    with pytest.raises(ValueError, match="breach_fraction"):
        generate(breach_fraction=1.5)


def test_generate_zero_tickers() -> None:
    assert generate(n_tickers=0, n_days=5) == []


def test_generate_with_breach_cohort() -> None:
    """At elevated breach_fraction, band breaches must surface."""
    from vnstock.anomaly import find_band_breaches

    bars = generate(
        n_tickers=20,
        n_days=20,
        seed=11,
        breach_fraction=0.2,
    )
    assert len(find_band_breaches(bars)) >= 1


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vnstock.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-stock-ticker-pipeline" in r.stdout


def test_cli_exchanges() -> None:
    r = _run("exchanges")
    assert r.returncode == 0
    assert "HOSE" in r.stdout
    assert "HNX" in r.stdout


def test_cli_tickers() -> None:
    r = _run("tickers")
    assert r.returncode == 0
    assert "VIC" in r.stdout
    assert "VNM" in r.stdout


def test_cli_band() -> None:
    r = _run(
        "band",
        "--reference",
        "50000",
        "--exchange",
        "HOSE",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["ceiling_vnd"] == 53_500
    assert payload["floor_vnd"] == 46_500


def test_cli_tick() -> None:
    r = _run(
        "tick",
        "--price",
        "5000",
        "--exchange",
        "HOSE",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["tick_vnd"] == 10


def test_cli_end_to_end(tmp_path: Path) -> None:
    bar_file = tmp_path / "bars.jsonl"
    summary_file = tmp_path / "summary.jsonl"

    r = _run(
        "simulate",
        "--tickers",
        "5",
        "--days",
        "10",
        "--seed",
        "7",
        "--output",
        str(bar_file),
    )
    assert r.returncode == 0, r.stderr
    assert bar_file.exists()

    r = _run(
        "summary",
        "--input",
        str(bar_file),
        "--output",
        str(summary_file),
        "--show",
        "0",
    )
    assert r.returncode == 0, r.stderr
    assert summary_file.exists()


def test_cli_anomaly_exit_code(tmp_path: Path) -> None:
    bar_file = tmp_path / "bars.jsonl"
    r = _run(
        "simulate",
        "--tickers",
        "5",
        "--days",
        "5",
        "--seed",
        "0",
        "--output",
        str(bar_file),
    )
    assert r.returncode == 0
    r = _run("anomaly", "--input", str(bar_file), "--show", "0")
    # Either 0 (no findings) or 2 (findings present).
    assert r.returncode in (0, 2), r.stderr
