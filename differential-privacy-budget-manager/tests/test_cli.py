"""CLI smoke tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dpbudget.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestCLI:
    def test_demo_default(self, capsys: object) -> None:
        main(["demo"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "Queries" in out or "allowed" in out

    def test_demo_quiet(self, capsys: object) -> None:
        main(["demo", "--quiet"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert out == ""

    def test_demo_writes_jsonl(self, tmp_path: Path) -> None:
        out_file = tmp_path / "audit.jsonl"
        main(["demo", "--quiet", "--output", str(out_file)])
        lines = [ln for ln in out_file.read_text().splitlines() if ln.strip()]
        assert len(lines) >= 1
        for ln in lines:
            obj = json.loads(ln)
            assert "query_id" in obj
            assert "status" in obj

    def test_query_command(self, capsys: object) -> None:
        main(["query", "100.0", "--epsilon", "1.0", "--sensitivity", "1.0"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "noisy" in out.lower()

    def test_compose_command(self, capsys: object) -> None:
        main(["compose", "0.5", "0.5", "1.0"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "Basic" in out
        assert "Advanced" in out

    def test_no_command_prints_help(self, capsys: object) -> None:
        main([])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "dpbudget" in out or "usage" in out.lower()
