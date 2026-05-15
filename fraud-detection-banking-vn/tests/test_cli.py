"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fraudvn.cli import main


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "fraud-detection-banking-vn" in out


def test_cli_simulate_to_file(tmp_path: Path):
    out = tmp_path / "txns.jsonl"
    rc = main(["simulate", "--benign", "5", "--seed", "1", "--output", str(out)])
    assert rc == 0
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 5


def test_cli_simulate_with_scams_then_evaluate(tmp_path: Path, capsys):
    txns_path = tmp_path / "txns.jsonl"
    decisions_path = tmp_path / "decisions.jsonl"
    main(
        [
            "simulate",
            "--benign",
            "5",
            "--inject-scams",
            "cong_an,crypto",
            "--seed",
            "1",
            "--output",
            str(txns_path),
        ]
    )
    rc = main(
        [
            "evaluate",
            "--input",
            str(txns_path),
            "--output",
            str(decisions_path),
        ]
    )
    assert rc == 0
    lines = [
        line for line in decisions_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    decisions = [json.loads(line) for line in lines]
    # Some non-ALLOW decisions for the scam txns.
    non_allow = [d for d in decisions if d["decision"] != "ALLOW"]
    assert non_allow


def test_cli_evaluate_summary(tmp_path: Path, capsys):
    txns_path = tmp_path / "txns.jsonl"
    main(
        [
            "simulate",
            "--benign",
            "3",
            "--inject-scams",
            "cong_an",
            "--seed",
            "1",
            "--output",
            str(txns_path),
        ]
    )
    rc = main(["evaluate", "--input", str(txns_path), "--summary"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "Summary:" in err
    assert "latency" in err


def test_cli_evaluate_blacklist_blocks(tmp_path: Path):
    txns_path = tmp_path / "txns.jsonl"
    decisions_path = tmp_path / "decisions.jsonl"
    main(
        [
            "simulate",
            "--benign",
            "0",
            "--blacklist-n",
            "1",
            "--blacklist",
            "BAD-001",
            "--seed",
            "1",
            "--output",
            str(txns_path),
        ]
    )
    rc = main(
        [
            "evaluate",
            "--input",
            str(txns_path),
            "--blacklist",
            "BAD-001",
            "--output",
            str(decisions_path),
        ]
    )
    assert rc == 0
    lines = [
        line for line in decisions_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    decisions = [json.loads(line) for line in lines]
    assert any(d["decision"] == "BLOCK" for d in decisions)


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
