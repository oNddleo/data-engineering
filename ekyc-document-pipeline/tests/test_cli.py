"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ekycpipe.cli import main


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "ekyc-document-pipeline" in out


def test_cli_parse_cccd(capsys):
    rc = main(["parse-cccd", "079095012345"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "079" in out
    assert "MALE" in out
    assert "1995" in out


def test_cli_parse_cccd_invalid_returns_2(capsys):
    rc = main(["parse-cccd", "000000000000"])
    assert rc == 2


def test_cli_simulate_to_file(tmp_path: Path):
    out = tmp_path / "data.json"
    rc = main(["simulate", "--citizens", "5", "--seed", "1", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload["images"]) == 5
    assert len(payload["bca"]) == 5


def test_cli_simulate_with_anomalies(tmp_path: Path):
    out = tmp_path / "data.json"
    main(
        [
            "simulate",
            "--citizens",
            "3",
            "--seed",
            "1",
            "--anomalies",
            "name_mismatch,bad_cccd",
            "--output",
            str(out),
        ]
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    # 3 clean + 2 anomalies = 5 OCR rows (anomaly always adds an image).
    assert len(payload["images"]) == 5


def test_cli_run_summarises(tmp_path: Path, capsys):
    data_path = tmp_path / "data.json"
    main(["simulate", "--citizens", "5", "--seed", "1", "--output", str(data_path)])
    rc = main(["run", "--dataset", str(data_path)])
    assert rc == 0
    out = capsys.readouterr().out
    summary = json.loads(out)
    assert summary["processed"] == 5
    assert summary["valid"] == 5
    assert summary["encrypted"] == 0  # no --with-encryption


def test_cli_run_with_encryption(tmp_path: Path, capsys):
    data_path = tmp_path / "data.json"
    main(["simulate", "--citizens", "3", "--seed", "1", "--output", str(data_path)])
    rc = main(
        [
            "run",
            "--dataset",
            str(data_path),
            "--with-encryption",
            "--encryption-seed",
            "test-seed",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    summary = json.loads(out)
    assert summary["encrypted"] == 3


def test_cli_demo_keygen_emits_64_hex_chars(capsys):
    rc = main(["demo-keygen"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert len(out) == 64
    int(out, 16)  # parses as hex


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
