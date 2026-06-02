"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from payroll.simulator import generate_employees, generate_periods


def test_generate_employees_count() -> None:
    assert len(generate_employees(n=10, seed=0)) == 10


def test_generate_employees_deterministic() -> None:
    a = generate_employees(n=5, seed=42)
    b = generate_employees(n=5, seed=42)
    assert a == b


def test_generate_employees_validates() -> None:
    with pytest.raises(ValueError):
        generate_employees(n=-1)


def test_generate_periods_per_employee() -> None:
    emps = generate_employees(n=5, seed=0)
    periods = generate_periods(emps, n_months=12, seed=0)
    assert len(periods) == 5 * 12


def test_generate_periods_validates() -> None:
    with pytest.raises(ValueError):
        generate_periods([], n_months=0)


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "payroll.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-payroll-pipeline" in r.stdout


def test_cli_brackets() -> None:
    r = _run("brackets")
    assert r.returncode == 0
    # Should have 7 lines plus header.
    assert "35.0%" in r.stdout
    assert "5.0%" in r.stdout


def test_cli_minwage() -> None:
    r = _run("minwage", "--region", "REGION_1")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["min_wage_vnd"] == 4_960_000


def test_cli_compute() -> None:
    r = _run(
        "compute",
        "--employee-id",
        "E-1",
        "--gross",
        "30000000",
        "--dependents",
        "1",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["gross_salary_vnd"] == 30_000_000
    assert payload["net_pay_vnd"] > 0


def test_cli_simulate(tmp_path: Path) -> None:
    out = tmp_path / "payslips.jsonl"
    r = _run(
        "simulate",
        "--employees",
        "5",
        "--months",
        "3",
        "--year",
        "2025",
        "--seed",
        "0",
        "--output",
        str(out),
        "--show",
        "0",
    )
    assert r.returncode == 0
    assert out.exists()
