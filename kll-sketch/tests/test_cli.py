"""CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "kllsketch.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert d["name"] == "kll-sketch"


def test_cli_demo() -> None:
    r = _run("demo", "--n", "1000", "--k", "100", "--seed", "0")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["n"] == 1000
    assert d["p50"] is not None
    assert d["size"] < 1000
