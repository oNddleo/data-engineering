"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sbv2345.cli import main


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "sbv-circular-2345-compliance-pipeline" in out


def test_cli_simulate_to_file(tmp_path: Path):
    out = tmp_path / "txns.jsonl"
    rc = main(["simulate", "--small", "5", "--large", "2", "--seed", "1", "--output", str(out)])
    assert rc == 0
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 7


def test_cli_ingest_pipeline(tmp_path: Path):
    txns_path = tmp_path / "txns.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    main(
        [
            "simulate",
            "--small",
            "0",
            "--large",
            "3",
            "--cumulative",
            "1",
            "--cross-border",
            "1",
            "--seed",
            "1",
            "--output",
            str(txns_path),
        ]
    )
    rc = main(["ingest", "--input", str(txns_path), "--output", str(ledger_path)])
    assert rc == 0
    lines = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    # 3 large + 1 cumulative pair (1 fires) + 1 cross-border = 5 audit events.
    assert len(lines) >= 5


def test_cli_verify_clean_ledger(tmp_path: Path, capsys):
    txns_path = tmp_path / "txns.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    main(["simulate", "--small", "0", "--large", "3", "--seed", "1", "--output", str(txns_path)])
    main(["ingest", "--input", str(txns_path), "--output", str(ledger_path)])
    rc = main(["verify", "--ledger", str(ledger_path)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "OK" in err


def test_cli_verify_detects_tamper(tmp_path: Path, capsys):
    txns_path = tmp_path / "txns.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    main(["simulate", "--small", "0", "--large", "3", "--seed", "1", "--output", str(txns_path)])
    main(["ingest", "--input", str(txns_path), "--output", str(ledger_path)])
    # Tamper with an amount.
    text = ledger_path.read_text(encoding="utf-8")
    ledger_path.write_text(text.replace("11", "99", 1), encoding="utf-8")
    rc = main(["verify", "--ledger", str(ledger_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "TAMPER" in err


def test_cli_seal_day(tmp_path: Path, capsys):
    txns_path = tmp_path / "txns.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    main(["simulate", "--small", "0", "--large", "4", "--seed", "1", "--output", str(txns_path)])
    main(["ingest", "--input", str(txns_path), "--output", str(ledger_path)])
    rc = main(["seal-day", "--ledger", str(ledger_path), "--day", "2026-05-14"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["day"] == "2026-05-14"
    assert payload["record_count"] >= 1
    assert len(payload["merkle_root"]) == 64


def test_cli_report_csv_format(tmp_path: Path, capsys):
    txns_path = tmp_path / "txns.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    main(["simulate", "--small", "0", "--large", "3", "--seed", "1", "--output", str(txns_path)])
    main(["ingest", "--input", str(txns_path), "--output", str(ledger_path)])
    rc = main(["report", "--ledger", str(ledger_path), "--format", "csv"])
    assert rc == 0
    out = capsys.readouterr().out
    first = out.splitlines()[0]
    assert "sequence_number,txn_id" in first


def test_cli_report_json_format(tmp_path: Path, capsys):
    txns_path = tmp_path / "txns.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    main(["simulate", "--small", "0", "--large", "3", "--seed", "1", "--output", str(txns_path)])
    main(["ingest", "--input", str(txns_path), "--output", str(ledger_path)])
    rc = main(["report", "--ledger", str(ledger_path), "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["total"] >= 1
    assert "by_trigger" in payload


def test_cli_retention(tmp_path: Path, capsys):
    txns_path = tmp_path / "txns.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    main(["simulate", "--small", "0", "--large", "2", "--seed", "1", "--output", str(txns_path)])
    main(["ingest", "--input", str(txns_path), "--output", str(ledger_path)])
    rc = main(["retention", "--ledger", str(ledger_path), "--today", "2026-06-01"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["total"] >= 1
    # Sealed in 2026, today 2026 → all should be ACTIVE.
    assert payload["active"] == payload["total"]


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
