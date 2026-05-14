"""CLI smoke tests — exercise the argparse wiring + end-to-end."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from n247mon.cli import main


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "napas-247-transaction-monitor" in out


def test_cli_simulate_stdout(capsys):
    rc = main(["simulate", "--txns", "5", "--seed", "1"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 5
    for line in lines:
        d = json.loads(line)
        assert "txn_id" in d
        assert "amount_vnd" in d


def test_cli_simulate_to_file(tmp_path: Path, capsys):
    out_path = tmp_path / "stream.jsonl"
    rc = main(["simulate", "--txns", "3", "--seed", "1", "--output", str(out_path)])
    assert rc == 0
    text = out_path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    assert len(lines) == 3


def test_cli_monitor_via_files(tmp_path: Path, capsys):
    # First simulate, then monitor.
    sim_path = tmp_path / "stream.jsonl"
    alerts_path = tmp_path / "alerts.jsonl"
    bl_path = tmp_path / "bl.txt"
    bl_path.write_text("0010001000\n# comment\n  \n", encoding="utf-8")
    main(
        [
            "simulate",
            "--txns",
            "0",
            "--seed",
            "1",
            "--inject",
            "bio_single,structuring",
            "--output",
            str(sim_path),
        ]
    )
    rc = main(
        [
            "monitor",
            "--input",
            str(sim_path),
            "--blacklist",
            str(bl_path),
            "--output",
            str(alerts_path),
        ]
    )
    assert rc == 0
    alerts_text = alerts_path.read_text(encoding="utf-8")
    lines = [line for line in alerts_text.splitlines() if line.strip()]
    kinds = {json.loads(line)["kind"] for line in lines}
    assert "BIO_REQUIRED_SINGLE_TXN" in kinds
    assert "STRUCTURING_SUSPECTED" in kinds


def test_cli_monitor_summary_goes_to_stderr(tmp_path: Path, capsys):
    sim_path = tmp_path / "stream.jsonl"
    main(
        [
            "simulate",
            "--txns",
            "0",
            "--seed",
            "1",
            "--inject",
            "bio_single",
            "--output",
            str(sim_path),
        ]
    )
    rc = main(["monitor", "--input", str(sim_path), "--summary"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "Summary:" in err
    assert "alerts" in err


def test_cli_monitor_from_stdin(tmp_path: Path, capsys, monkeypatch):
    import io as _io

    sim_path = tmp_path / "stream.jsonl"
    main(
        [
            "simulate",
            "--txns",
            "0",
            "--seed",
            "1",
            "--inject",
            "bio_single",
            "--output",
            str(sim_path),
        ]
    )
    monkeypatch.setattr("sys.stdin", _io.StringIO(sim_path.read_text(encoding="utf-8")))
    rc = main(["monitor"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "BIO_REQUIRED_SINGLE_TXN" in out


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
