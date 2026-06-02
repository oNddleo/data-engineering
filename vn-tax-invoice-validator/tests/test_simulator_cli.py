"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vntax.cli import main
from vntax.simulator import generate
from vntax.validator import Severity, validate


def test_simulate_deterministic():
    a = generate(n_invoices=20, bad_fraction=0.3, seed=42)
    b = generate(n_invoices=20, bad_fraction=0.3, seed=42)
    assert [i.invoice_id for i in a] == [i.invoice_id for i in b]


def test_simulate_emits_n_invoices():
    invoices = generate(n_invoices=37, bad_fraction=0.0, seed=1)
    assert len(invoices) == 37


def test_simulate_zero_bad_fraction_all_clean():
    invoices = generate(n_invoices=50, bad_fraction=0.0, seed=2)
    n_bad = sum(1 for inv in invoices if any(f.severity is Severity.ERROR for f in validate(inv)))
    assert n_bad == 0


def test_simulate_high_bad_fraction_produces_errors():
    invoices = generate(n_invoices=50, bad_fraction=1.0, seed=3)
    n_bad = sum(1 for inv in invoices if any(f.severity is Severity.ERROR for f in validate(inv)))
    # Some bugs (e.g. wrong-template on EXPORT) silently no-op, so not all
    # 100% bad invoices produce errors. But the majority should.
    assert n_bad >= 30


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_invoices=0)
    with pytest.raises(ValueError):
        generate(bad_fraction=1.5)


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "vn-tax-invoice-validator" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    inv_path = tmp_path / "invoices.jsonl"
    rc = main(
        [
            "simulate",
            "--n",
            "40",
            "--bad-fraction",
            "0.30",
            "--seed",
            "0",
            "--output",
            str(inv_path),
        ]
    )
    assert rc == 0
    assert inv_path.is_file()
    capsys.readouterr()

    findings_path = tmp_path / "findings.jsonl"
    rc = main(["validate", "--input", str(inv_path), "--output", str(findings_path), "--summary"])
    assert rc == 0
    assert findings_path.is_file()
    capsys.readouterr()  # drain --summary one-liner so it doesn't leak into next assertion

    rc = main(["summary", "--input", str(inv_path)])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_invoices"] == 40
    assert "by_code" in payload


def test_cli_lookup_known_mst(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["lookup", "0100109106"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["name"] == "Vietcombank"


def test_cli_lookup_bad_checksum_returns_1(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["lookup", "0100109107"])
    capsys.readouterr()
    assert rc == 1


def test_cli_lookup_unknown_but_valid_returns_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Valid checksum (compute_check_digit for 000000000 = 0).
    rc = main(["lookup", "0000000000"])
    capsys.readouterr()
    assert rc == 2  # checksum OK, not in registry
