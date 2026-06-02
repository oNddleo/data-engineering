"""CLI smoke tests."""

from __future__ import annotations

import json

import pytest

from raftmeta.cli import main


class TestCLI:
    def test_demo_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["demo", "--nodes", "3", "--writes", "3", "--seed", "1"])
        out = capsys.readouterr().out
        lines = [ln for ln in out.strip().splitlines() if ln]
        assert len(lines) >= 1
        first = json.loads(lines[0])
        assert "leader" in first

    def test_demo_shows_keys(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["demo", "--nodes", "3", "--writes", "5", "--seed", "2"])
        out = capsys.readouterr().out
        lines = [ln for ln in out.strip().splitlines() if ln]
        last = json.loads(lines[-1])
        assert "keys" in last
        assert len(last["keys"]) >= 5

    def test_snapshot_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["snapshot", "--nodes", "3", "--writes", "2", "--seed", "3"])
        out = capsys.readouterr().out
        lines = [ln for ln in out.strip().splitlines() if ln]
        assert len(lines) == 3  # one line per node
        for ln in lines:
            row = json.loads(ln)
            assert "node_id" in row
            assert "state" in row
            assert "term" in row

    def test_help_exits_0(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    def test_five_node_demo(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["demo", "--nodes", "5", "--writes", "3", "--seed", "7"])
        out = capsys.readouterr().out
        lines = [ln for ln in out.strip().splitlines() if ln]
        assert len(lines) >= 1
        assert "leader" in json.loads(lines[0])
