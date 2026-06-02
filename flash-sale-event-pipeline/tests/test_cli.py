"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flashpipe.cli import main


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "flash-sale-event-pipeline" in out


def test_cli_simulate(tmp_path: Path):
    out = tmp_path / "events.jsonl"
    rc = main(["simulate", "--events", "20", "--seed", "1", "--output", str(out)])
    assert rc == 0
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 20


def test_cli_run_basic(tmp_path: Path, capsys):
    events_path = tmp_path / "events.jsonl"
    main(["simulate", "--events", "100", "--seed", "1", "--output", str(events_path)])
    rc = main(
        [
            "run",
            "--input",
            str(events_path),
            "--window",
            "1",
            "--oo",
            "0",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["n_aggregates"] >= 1
    assert "metrics" in payload


def test_cli_run_with_outputs(tmp_path: Path):
    events_path = tmp_path / "events.jsonl"
    win_path = tmp_path / "windows.jsonl"
    hot_path = tmp_path / "hotness.jsonl"
    main(
        [
            "simulate",
            "--events",
            "200",
            "--seed",
            "1",
            "--stampede-item",
            "100005",
            "--output",
            str(events_path),
        ]
    )
    rc = main(
        [
            "run",
            "--input",
            str(events_path),
            "--window",
            "1",
            "--stampede-mul",
            "3",
            "--output-windows",
            str(win_path),
            "--output-hotness",
            str(hot_path),
        ]
    )
    assert rc == 0
    assert win_path.exists()
    assert hot_path.exists()


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
