"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vnbhyt.simulator import generate


def test_generate_count() -> None:
    assert len(generate(n=50, seed=0)) == 50


def test_generate_deterministic() -> None:
    assert generate(n=20, seed=42) == generate(n=20, seed=42)


def test_generate_rejects_negative() -> None:
    with pytest.raises(ValueError):
        generate(n=-1)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vnbhyt.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-insurance-claim-pipeline" in r.stdout


def test_cli_end_to_end(tmp_path: Path) -> None:
    claims_file = tmp_path / "claims.jsonl"
    payouts_file = tmp_path / "payouts.jsonl"

    r = _run("simulate", "--n", "40", "--seed", "0", "--output", str(claims_file))
    assert r.returncode == 0, r.stderr

    r = _run("payout", "--input", str(claims_file), "--output", str(payouts_file))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["count"] == 40
    assert payload["total_insurance_payout_vnd"] >= 0
    assert payouts_file.exists()
