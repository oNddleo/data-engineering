"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dqkit.cli import main
from dqkit.simulator import generate


def test_simulate_deterministic():
    a = generate(n_rows=20, seed=42)
    b = generate(n_rows=20, seed=42)
    assert a == b


def test_simulate_emits_n_rows():
    rows = generate(n_rows=50, defect_fraction=0.0, seed=1)
    assert len(rows) == 50


def test_simulate_zero_defects_all_columns_present():
    rows = generate(n_rows=10, defect_fraction=0.0, seed=2)
    expected_cols = {
        "customer_id",
        "cccd",
        "mst",
        "phone",
        "bank_account",
        "postal_code",
        "tier",
        "credit_limit_vnd",
    }
    for row in rows:
        assert set(row) == expected_cols


def test_simulate_high_defect_fraction_produces_defects():
    rows = generate(n_rows=100, defect_fraction=1.0, seed=3)
    # Some rows should have null cccd / mst / etc.
    n_null_cccd = sum(1 for r in rows if r["cccd"] is None)
    assert n_null_cccd > 0


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_rows=0)
    with pytest.raises(ValueError):
        generate(defect_fraction=1.5)


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "dwh-data-quality-toolkit" in out
    assert "cccd" in out


def test_cli_checks(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["checks"])
    out = capsys.readouterr().out
    assert rc == 0
    for name in ("cccd", "mst", "not_null", "unique", "vn_phone"):
        assert name in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rows_path = tmp_path / "customers.jsonl"
    suite_path = tmp_path / "suite.json"
    results_path = tmp_path / "results.jsonl"
    qd = tmp_path / "q"

    rc = main(
        [
            "simulate",
            "--rows",
            "30",
            "--defect-fraction",
            "0.30",
            "--seed",
            "0",
            "--output",
            str(rows_path),
        ]
    )
    assert rc == 0
    capsys.readouterr()

    rc = main(["make-suite", "--output", str(suite_path)])
    assert rc == 0
    capsys.readouterr()

    rc = main(
        [
            "run",
            "--input",
            str(rows_path),
            "--suite",
            str(suite_path),
            "--results-output",
            str(results_path),
            "--quarantine-dir",
            str(qd),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["n_checks"] == 9
    # ERROR-severity failures exit with code 2.
    assert rc in (0, 2)
    assert (qd / "good.jsonl").is_file()
    assert (qd / "bad.jsonl").is_file()


def test_cli_clean_data_exits_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A defect-free rowset against the same suite should exit 0."""
    rows_path = tmp_path / "customers.jsonl"
    suite_path = tmp_path / "suite.json"
    rc = main(
        [
            "simulate",
            "--rows",
            "20",
            "--defect-fraction",
            "0.0",
            "--seed",
            "0",
            "--output",
            str(rows_path),
        ]
    )
    capsys.readouterr()
    rc = main(["make-suite", "--output", str(suite_path)])
    capsys.readouterr()
    rc = main(["run", "--input", str(rows_path), "--suite", str(suite_path)])
    capsys.readouterr()
    assert rc == 0
