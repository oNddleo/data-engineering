"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from amlgraph.cli import main


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "anti-money-laundering-graph" in out


def test_cli_simulate_to_file(tmp_path: Path):
    out = tmp_path / "data.json"
    rc = main(
        ["simulate", "--accounts", "10", "--normal", "20", "--seed", "1", "--output", str(out)]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload["accounts"]) >= 10
    assert len(payload["transactions"]) >= 20


def test_cli_detect_fires_on_injected_patterns(tmp_path: Path):
    data_path = tmp_path / "data.json"
    alerts_path = tmp_path / "alerts.jsonl"
    main(
        [
            "simulate",
            "--accounts",
            "5",
            "--normal",
            "0",
            "--fan-out",
            "1",
            "--round-trip",
            "1",
            "--seed",
            "1",
            "--output",
            str(data_path),
        ]
    )
    rc = main(["detect", "--dataset", str(data_path), "--output", str(alerts_path)])
    assert rc == 0
    lines = [line for line in alerts_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    kinds = {json.loads(line)["kind"] for line in lines}
    assert "FAN_OUT" in kinds
    assert "ROUND_TRIP" in kinds


def test_cli_detect_summary(tmp_path: Path, capsys):
    data_path = tmp_path / "data.json"
    main(
        [
            "simulate",
            "--accounts",
            "5",
            "--normal",
            "0",
            "--layering",
            "1",
            "--seed",
            "1",
            "--output",
            str(data_path),
        ]
    )
    rc = main(["detect", "--dataset", str(data_path), "--summary"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "Summary:" in err


def test_cli_rank_returns_topn(tmp_path: Path, capsys):
    data_path = tmp_path / "data.json"
    alerts_path = tmp_path / "alerts.jsonl"
    main(
        [
            "simulate",
            "--accounts",
            "5",
            "--normal",
            "0",
            "--fan-out",
            "1",
            "--round-trip",
            "1",
            "--seed",
            "1",
            "--output",
            str(data_path),
        ]
    )
    main(["detect", "--dataset", str(data_path), "--output", str(alerts_path)])
    rc = main(["rank", "--dataset", str(data_path), "--alerts", str(alerts_path), "--n", "5"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) >= 1
    # Each line: account_id<TAB>score
    parts = lines[0].split("\t")
    assert len(parts) == 2
    int(parts[1])  # parses as int


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
