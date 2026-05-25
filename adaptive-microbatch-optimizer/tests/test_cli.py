"""CLI smoke tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from microbatch.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestCLI:
    def test_simulate_default(self, capsys: object) -> None:
        main(["simulate", "--steps", "5"])
        out = capsys.readouterr().out
        assert "step=" in out

    def test_simulate_quiet(self, capsys: object) -> None:
        main(["simulate", "--steps", "5", "--quiet"])
        out = capsys.readouterr().out
        assert out == ""

    def test_simulate_writes_trace(self, tmp_path: Path) -> None:
        out_file = tmp_path / "trace.jsonl"
        main(["simulate", "--steps", "10", "--quiet", "--output", str(out_file)])
        rows = [json.loads(ln) for ln in out_file.read_text().splitlines() if ln.strip()]
        assert len(rows) == 10
        assert all("window_s" in r for r in rows)

    def test_simulate_writes_snapshot(self, tmp_path: Path) -> None:
        snap_file = tmp_path / "snaps.jsonl"
        main(["simulate", "--steps", "5", "--quiet", "--snapshot", str(snap_file)])
        lines = [ln for ln in snap_file.read_text().splitlines() if ln.strip()]
        assert len(lines) == 5

    def test_summary_from_trace(self, tmp_path: Path, capsys: object) -> None:
        trace = tmp_path / "t.jsonl"
        main(["simulate", "--steps", "20", "--quiet", "--output", str(trace)])
        main(["summary", str(trace)])
        out = capsys.readouterr().out
        assert "window_s" in out
        assert "latency_s" in out

    def test_summary_missing_file(self, tmp_path: Path, capsys: object) -> None:
        path = tmp_path / "missing.jsonl"
        try:
            main(["summary", str(path)])
        except SystemExit as exc:
            assert exc.code == 1
        err = capsys.readouterr().err
        assert "not found" in err

    def test_no_command_prints_help(self, capsys: object) -> None:
        main([])
        out = capsys.readouterr().out
        assert "microbatch" in out or "usage" in out.lower()
