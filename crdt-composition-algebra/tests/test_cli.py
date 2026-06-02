"""CLI smoke tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from crdt.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestCLI:
    def test_demo_default(self, capsys: object) -> None:
        main(["demo"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "GCounter" in out or "merged" in out

    def test_demo_quiet(self, capsys: object) -> None:
        main(["demo", "--quiet"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert out == ""

    def test_demo_writes_snapshot(self, tmp_path: Path) -> None:
        out_file = tmp_path / "snap.jsonl"
        main(["demo", "--quiet", "--output", str(out_file)])
        rows = [json.loads(ln) for ln in out_file.read_text().splitlines() if ln.strip()]
        assert len(rows) >= 2
        assert any(r.get("crdt") == "GCounter" for r in rows)

    def test_verify_passes(self, capsys: object) -> None:
        main(["verify", "--rounds", "10", "--seed", "1"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "passed" in out

    def test_verify_quiet(self, capsys: object) -> None:
        main(["verify", "--quiet", "--rounds", "5"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert out == ""

    def test_no_command_prints_help(self, capsys: object) -> None:
        main([])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "crdt" in out or "usage" in out.lower()
