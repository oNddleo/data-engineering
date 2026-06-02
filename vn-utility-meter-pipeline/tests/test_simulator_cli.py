"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evn.simulator import generate


def test_generate_default() -> None:
    readings = generate(n_customers=5, n_months=3, seed=0)
    # 5 customers × 3 months = 15 readings.
    assert len(readings) == 15


def test_generate_deterministic() -> None:
    a = generate(n_customers=5, n_months=3, seed=42)
    b = generate(n_customers=5, n_months=3, seed=42)
    assert a == b


def test_generate_validates() -> None:
    with pytest.raises(ValueError, match="n_customers"):
        generate(n_customers=-1)
    with pytest.raises(ValueError, match="n_months"):
        generate(n_months=0)
    with pytest.raises(ValueError, match="n_months"):
        generate(n_months=13)
    with pytest.raises(ValueError, match="tampering_fraction"):
        generate(tampering_fraction=1.5)


def test_generate_zero_customers() -> None:
    assert generate(n_customers=0, n_months=3) == []


def test_generate_categories_present() -> None:
    """A reasonable sample should hit multiple categories."""
    from evn.schema import CustomerCategory

    readings = generate(n_customers=100, n_months=2, seed=11)
    cats = {r.category for r in readings}
    # Should hit at least HOUSEHOLD and one non-HOUSEHOLD with 100 customers.
    assert CustomerCategory.HOUSEHOLD in cats
    assert len(cats) >= 2


def test_generate_with_anomaly_cohorts() -> None:
    """At elevated fractions, anomaly detectors must fire."""
    from evn.anomaly import find_sudden_drops, find_unrealistic_spikes

    readings = generate(
        n_customers=100,
        n_months=12,
        seed=11,
        tampering_fraction=0.10,
        spike_fraction=0.10,
    )
    assert len(find_sudden_drops(readings)) >= 1
    assert len(find_unrealistic_spikes(readings)) >= 1


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "evn.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-utility-meter-pipeline" in r.stdout


def test_cli_units() -> None:
    r = _run("units")
    assert r.returncode == 0
    assert "PA" in r.stdout
    assert "EVNHCMC" in r.stdout


def test_cli_tariff() -> None:
    r = _run("tariff", "--date", "2025-01-15")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["decision"] == "2699/QĐ-BCT"
    assert len(payload["household_tiers"]) == 6


def test_cli_end_to_end(tmp_path: Path) -> None:
    reading_file = tmp_path / "readings.jsonl"
    bill_file = tmp_path / "bills.jsonl"

    r = _run(
        "simulate",
        "--customers",
        "10",
        "--months",
        "3",
        "--seed",
        "7",
        "--output",
        str(reading_file),
    )
    assert r.returncode == 0, r.stderr
    assert reading_file.exists()

    r = _run(
        "bill",
        "--input",
        str(reading_file),
        "--output",
        str(bill_file),
        "--show",
        "0",
    )
    assert r.returncode == 0, r.stderr
    assert bill_file.exists()

    r = _run(
        "summary",
        "--input",
        str(reading_file),
        "--show",
        "0",
    )
    assert r.returncode == 0


def test_cli_anomaly_exit_code(tmp_path: Path) -> None:
    reading_file = tmp_path / "readings.jsonl"
    r = _run(
        "simulate",
        "--customers",
        "5",
        "--months",
        "3",
        "--seed",
        "0",
        "--output",
        str(reading_file),
    )
    assert r.returncode == 0
    r = _run("anomaly", "--input", str(reading_file), "--show", "0")
    # Exit 0 (no findings) or 2 (findings present); not 1.
    assert r.returncode in (0, 2), r.stderr
