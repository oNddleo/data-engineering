"""CLI smoke tests for bftstream."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bftstream.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestCLI:
    def test_simulate_default(self, capsys: object) -> None:
        main(["simulate", "--nodes", "4", "--faults", "1", "--window-size", "5", "--windows", "1"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "window=" in out

    def test_simulate_quiet(self, capsys: object) -> None:
        main(["simulate", "--quiet", "--nodes", "4", "--faults", "1", "--window-size", "3"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert out == ""

    def test_simulate_writes_output(self, tmp_path: Path) -> None:
        out_file = tmp_path / "out.jsonl"
        main(
            [
                "simulate",
                "--quiet",
                "--nodes",
                "4",
                "--faults",
                "1",
                "--window-size",
                "5",
                "--windows",
                "2",
                "--output",
                str(out_file),
            ]
        )
        rows = [json.loads(ln) for ln in out_file.read_text().splitlines() if ln.strip()]
        assert len(rows) == 2
        assert all("window_id" in r for r in rows)

    def test_summary_command(self, tmp_path: Path, capsys: object) -> None:
        out_file = tmp_path / "wins.jsonl"
        main(
            [
                "simulate",
                "--quiet",
                "--nodes",
                "4",
                "--faults",
                "1",
                "--window-size",
                "5",
                "--windows",
                "3",
                "--output",
                str(out_file),
            ]
        )
        main(["summary", str(out_file)])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "windows" in out
        assert "total_records" in out

    def test_summary_missing_file(self, tmp_path: Path, capsys: object) -> None:
        try:
            main(["summary", str(tmp_path / "missing.jsonl")])
        except SystemExit as exc:
            assert exc.code == 1
        err = capsys.readouterr().err  # type: ignore[attr-defined]
        assert "not found" in err

    def test_invalid_faults(self, capsys: object) -> None:
        try:
            main(["simulate", "--quiet", "--nodes", "3", "--faults", "1"])
        except SystemExit as exc:
            assert exc.code == 1
        err = capsys.readouterr().err  # type: ignore[attr-defined]
        assert "3f+1" in err or "need" in err

    def test_no_command_prints_help(self, capsys: object) -> None:
        main([])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "bftstream" in out or "usage" in out.lower()
