"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bhyt.calculator import calculate
from bhyt.card import is_valid_format
from bhyt.cli import main
from bhyt.simulator import generate


def test_simulate_deterministic():
    a = generate(n_patients=10, n_claims=20, seed=42)
    b = generate(n_patients=10, n_claims=20, seed=42)
    assert [p.patient_id for p in a[0]] == [p.patient_id for p in b[0]]
    assert [c.claim_id for c in a[2]] == [c.claim_id for c in b[2]]


def test_simulate_card_numbers_valid():
    _, cards, _ = generate(n_patients=20, n_claims=30, seed=1)
    for card in cards:
        assert is_valid_format(card.card_number)


def test_simulate_claims_reference_real_patients():
    patients, _, claims = generate(n_patients=10, n_claims=30, seed=2)
    patient_ids = {p.patient_id for p in patients}
    for c in claims:
        assert c.patient_id in patient_ids


def test_simulate_claims_have_valid_subtotal():
    _, _, claims = generate(n_patients=5, n_claims=20, seed=3)
    for c in claims:
        expected = sum(it.line_total_vnd for it in c.items)
        assert c.subtotal_vnd == expected


def test_simulator_to_calculator_pipeline():
    """All simulator-generated claims compute valid reimbursements."""
    _, _, claims = generate(n_patients=5, n_claims=15, seed=4)
    for c in claims:
        r = calculate(c)
        # Co-pay covers exactly what insurer doesn't.
        assert r.insurer_pays_vnd + r.patient_pays_vnd == r.subtotal_vnd
        # Insurer never pays more than subtotal.
        assert 0 <= r.insurer_pays_vnd <= r.subtotal_vnd


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_patients=0)
    with pytest.raises(ValueError):
        generate(n_claims=0)


# ---------- CLI ----------------------------------------------------------


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "healthcare-claims-processor" in out


def test_cli_decode_valid(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["decode", "D40179012345678"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["category"] == "UU_TIEN_4"


def test_cli_decode_invalid_returns_1(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["decode", "BAD"])
    capsys.readouterr()
    assert rc == 1


def test_cli_icd_known(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["icd", "I10"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert "Tăng huyết áp" in payload["name_vi"]


def test_cli_icd_unknown_returns_1(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["icd", "Z99"])
    capsys.readouterr()
    assert rc == 1


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    rc = main(
        [
            "simulate",
            "--patients",
            "10",
            "--claims",
            "30",
            "--seed",
            "0",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    assert (out_dir / "claims.jsonl").is_file()
    capsys.readouterr()

    reimb = tmp_path / "reimb.jsonl"
    rc = main(
        ["calc", "--input", str(out_dir / "claims.jsonl"), "--output", str(reimb), "--show", "3"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert reimb.is_file()
    assert "claim" in out

    rc = main(["summary", "--input", str(out_dir / "claims.jsonl")])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_claims"] == 30
    assert "by_category" in payload
    assert "by_care_level" in payload


def test_cli_calc_emergency_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The --emergency flag waives the referral penalty for every claim."""
    out_dir = tmp_path / "raw"
    main(
        ["simulate", "--patients", "5", "--claims", "10", "--seed", "0", "--out-dir", str(out_dir)]
    )
    capsys.readouterr()

    reimb_normal = tmp_path / "normal.jsonl"
    main(["calc", "--input", str(out_dir / "claims.jsonl"), "--output", str(reimb_normal)])
    capsys.readouterr()

    reimb_emerg = tmp_path / "emerg.jsonl"
    main(
        [
            "calc",
            "--input",
            str(out_dir / "claims.jsonl"),
            "--output",
            str(reimb_emerg),
            "--emergency",
        ]
    )
    capsys.readouterr()

    # Emergency calc pays >= normal calc in all cases (waived penalty).
    from bhyt.io_jsonl import load_reimbursements

    normal = load_reimbursements(reimb_normal.read_text())
    emerg = load_reimbursements(reimb_emerg.read_text())
    for n, e in zip(normal, emerg, strict=True):
        assert e.insurer_pays_vnd >= n.insurer_pays_vnd
