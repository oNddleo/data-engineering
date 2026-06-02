"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cicscore.cli import main


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "credit-scoring-pipeline-vn" in out


def test_cli_simulate_to_file(tmp_path: Path):
    out = tmp_path / "borrowers.jsonl"
    rc = main(["simulate", "--borrowers", "5", "--seed", "1", "--output", str(out)])
    assert rc == 0
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 5


def test_cli_simulate_extract_score_pipeline(tmp_path: Path, capsys):
    bpath = tmp_path / "borrowers.jsonl"
    main(
        [
            "simulate",
            "--borrowers",
            "10",
            "--seed",
            "1",
            "--observation-date",
            "2026-05-14",
            "--output",
            str(bpath),
        ]
    )
    fpath = tmp_path / "features.jsonl"
    main(
        [
            "extract",
            "--input",
            str(bpath),
            "--observation-date",
            "2026-05-14",
            "--output",
            str(fpath),
        ]
    )
    f_lines = [line for line in fpath.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(f_lines) == 10
    # Each line should be parseable JSON with a score-able shape.
    for line in f_lines:
        payload = json.loads(line)
        assert "borrower_id" in payload
        assert "max_group_24m" in payload
    spath = tmp_path / "scores.jsonl"
    rc = main(
        [
            "score",
            "--input",
            str(bpath),
            "--observation-date",
            "2026-05-14",
            "--output",
            str(spath),
        ]
    )
    assert rc == 0
    s_lines = [line for line in spath.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(s_lines) == 10
    for line in s_lines:
        payload = json.loads(line)
        assert 300 <= payload["score"] <= 900


def test_cli_inspect(tmp_path: Path, capsys):
    bpath = tmp_path / "borrowers.jsonl"
    main(
        [
            "simulate",
            "--borrowers",
            "3",
            "--seed",
            "1",
            "--observation-date",
            "2026-05-14",
            "--output",
            str(bpath),
        ]
    )
    rc = main(
        [
            "inspect",
            "--input",
            str(bpath),
            "--observation-date",
            "2026-05-14",
            "--borrower-id",
            "NB-000000",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "score =" in out
    assert "NB-000000" in out


def test_cli_inspect_unknown_borrower(tmp_path: Path):
    bpath = tmp_path / "borrowers.jsonl"
    main(
        [
            "simulate",
            "--borrowers",
            "3",
            "--seed",
            "1",
            "--observation-date",
            "2026-05-14",
            "--output",
            str(bpath),
        ]
    )
    rc = main(
        [
            "inspect",
            "--input",
            str(bpath),
            "--observation-date",
            "2026-05-14",
            "--borrower-id",
            "DOES-NOT-EXIST",
        ]
    )
    assert rc == 1


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
