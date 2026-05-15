"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from multiprice.cli import main


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "multi-platform-price-tracker" in out


def test_cli_simulate(tmp_path: Path):
    out_dir = tmp_path / "data"
    rc = main(
        [
            "simulate",
            "--skus",
            "5",
            "--snapshots",
            "3",
            "--seed",
            "1",
            "--output",
            str(out_dir),
        ]
    )
    assert rc == 0
    assert (out_dir / "mappings.jsonl").exists()
    assert (out_dir / "observations.jsonl").exists()


def test_cli_changes(tmp_path: Path, capsys):
    out_dir = tmp_path / "data"
    main(["simulate", "--skus", "5", "--snapshots", "3", "--seed", "1", "--output", str(out_dir)])
    rc = main(["changes", "--dataset", str(out_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total:" in out


def test_cli_arbitrage(tmp_path: Path, capsys):
    out_dir = tmp_path / "data"
    main(
        [
            "simulate",
            "--skus",
            "5",
            "--snapshots",
            "2",
            "--arbitrage",
            "2",
            "--seed",
            "1",
            "--output",
            str(out_dir),
        ]
    )
    rc = main(["arbitrage", "--dataset", str(out_dir), "--min-spread", "10"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "arbitrage opportunities" in out


def test_cli_stockouts(tmp_path: Path, capsys):
    out_dir = tmp_path / "data"
    main(
        [
            "simulate",
            "--skus",
            "5",
            "--snapshots",
            "2",
            "--stockouts",
            "2",
            "--seed",
            "1",
            "--output",
            str(out_dir),
        ]
    )
    rc = main(["stockouts", "--dataset", str(out_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "stockouts" in out


def test_cli_summary_json(tmp_path: Path, capsys):
    out_dir = tmp_path / "data"
    main(
        [
            "simulate",
            "--skus",
            "4",
            "--snapshots",
            "3",
            "--arbitrage",
            "1",
            "--stockouts",
            "1",
            "--seed",
            "1",
            "--output",
            str(out_dir),
        ]
    )
    rc = main(["summary", "--dataset", str(out_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["n_skus"] == 4
    assert "n_arbitrage_opportunities" in payload


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
