"""CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "schemreg.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert "BACKWARD" in d["compatibility_modes"]


def test_cli_demo() -> None:
    r = _run("demo")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert d["versions"] == [1, 2]


def test_cli_check_compatible() -> None:
    old = json.dumps({"id": "int", "name": "str"})
    new = json.dumps({"id": "int", "name": "str", "?email": "str"})
    r = _run("check", "--old-schema", old, "--new-schema", new, "--mode", "BACKWARD")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert d["compatible"] is True


def test_cli_check_incompatible() -> None:
    old = json.dumps({"id": "int", "name": "str"})
    new = json.dumps({"id": "int"})  # removed required "name"
    r = _run("check", "--old-schema", old, "--new-schema", new, "--mode", "BACKWARD")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert d["compatible"] is False
    assert len(d["violations"]) > 0
