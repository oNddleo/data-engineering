"""Simulator + CLI smoke tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from vnbank.simulator import generate

# ---------- simulator -------------------------------------------------------


def test_generate_default() -> None:
    txns = generate(n_accounts=5, n_days=3, seed=0)
    assert len(txns) > 0


def test_generate_deterministic() -> None:
    a = generate(n_accounts=5, n_days=3, seed=42)
    b = generate(n_accounts=5, n_days=3, seed=42)
    assert a == b


def test_generate_zero_accounts() -> None:
    assert generate(n_accounts=0, n_days=3) == []


def test_generate_validates() -> None:
    with pytest.raises(ValueError, match="n_accounts"):
        generate(n_accounts=-1)
    with pytest.raises(ValueError, match="n_days"):
        generate(n_days=0)
    with pytest.raises(ValueError, match="ctr_fraction"):
        generate(ctr_fraction=1.5)


def test_generate_sorted_by_time() -> None:
    txns = generate(n_accounts=5, n_days=3, seed=0)
    times = [t.occurred_at for t in txns]
    assert times == sorted(times)


def test_generate_includes_aml_positive() -> None:
    """With AML fractions set higher, simulator must inject patterns."""
    txns = generate(
        n_accounts=50,
        n_days=10,
        seed=11,
        ctr_fraction=0.10,
        structuring_fraction=0.10,
        velocity_fraction=0.10,
    )
    from vnbank.aml import find_ctr, find_high_velocity, find_structuring

    assert len(find_ctr(txns)) >= 1
    assert len(find_structuring(txns)) >= 1
    assert len(find_high_velocity(txns)) >= 1


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vnbank.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-banking-transaction-pipeline" in r.stdout


def test_cli_banks() -> None:
    r = _run("banks")
    assert r.returncode == 0
    assert "VCB" in r.stdout
    assert "BIDV" in r.stdout


def test_cli_qr_build_and_parse() -> None:
    r = _run(
        "qr",
        "--bank-bin",
        "970436",
        "--account-number",
        "1234567890",
        "--amount",
        "100000",
    )
    assert r.returncode == 0
    payload = r.stdout.strip()
    assert "970436" in payload

    r2 = _run("qr", "--parse", payload)
    assert r2.returncode == 0
    assert "970436" in r2.stdout
    assert "100000" in r2.stdout


def test_cli_route() -> None:
    r = _run(
        "route",
        "--sender-bin",
        "970436",
        "--receiver-bin",
        "970418",
        "--amount",
        "100000",
    )
    assert r.returncode == 0
    assert "NAPAS_247" in r.stdout


def test_cli_end_to_end(tmp_path: Path) -> None:
    txn_file = tmp_path / "txns.jsonl"
    summary_file = tmp_path / "summaries.jsonl"

    r = _run(
        "simulate",
        "--accounts",
        "10",
        "--days",
        "5",
        "--seed",
        "7",
        "--output",
        str(txn_file),
    )
    assert r.returncode == 0, r.stderr
    assert txn_file.exists()

    r = _run(
        "summary",
        "--input",
        str(txn_file),
        "--output",
        str(summary_file),
        "--show",
        "0",
    )
    assert r.returncode == 0, r.stderr
    assert summary_file.exists()

    r = _run("aml", "--input", str(txn_file), "--show", "0")
    # Exit 0 or 2 depending on whether AML fires.
    assert r.returncode in (0, 2), r.stderr
