"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemaev.cli import main
from schemaev.compat import check_backward, check_forward
from schemaev.simulator import all_mutations, generate_pair


def test_simulator_supports_all_mutations():
    """Every advertised mutation produces a valid (old, new) pair."""
    for mutation in all_mutations():
        old, new = generate_pair(mutation=mutation)
        assert old.name == new.name
        assert old.fields  # non-empty


def test_safe_add_is_backward_and_forward_compatible():
    old, new = generate_pair(mutation="safe_add")
    assert check_backward(old, new).is_compatible is True
    assert check_forward(old, new).is_compatible is True


def test_required_add_breaks_backward():
    old, new = generate_pair(mutation="required_add")
    assert check_backward(old, new).is_compatible is False


def test_widen_type_breaks_forward_only():
    old, new = generate_pair(mutation="widen_type")
    assert check_backward(old, new).is_compatible is True
    assert check_forward(old, new).is_compatible is False


def test_narrow_type_breaks_backward_only():
    old, new = generate_pair(mutation="narrow_type")
    assert check_backward(old, new).is_compatible is False
    assert check_forward(old, new).is_compatible is True


def test_rename_with_alias_is_backward_compatible():
    old, new = generate_pair(mutation="rename_with_alias")
    assert check_backward(old, new).is_compatible is True


def test_simulator_unknown_mutation_raises():
    with pytest.raises(ValueError):
        generate_pair(mutation="some_unknown_thing")


# ---------- CLI ----------------------------------------------------------


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "schema-registry-evolution" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    rc = main(["simulate", "--mutation", "safe_add", "--out-dir", str(out_dir)])
    assert rc == 0
    assert (out_dir / "old.json").is_file()
    assert (out_dir / "new.json").is_file()
    capsys.readouterr()

    rc = main(["diff", "--old", str(out_dir / "old.json"), "--new", str(out_dir / "new.json")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ADDED" in out

    rc = main(
        [
            "compat",
            "--old",
            str(out_dir / "old.json"),
            "--new",
            str(out_dir / "new.json"),
            "--mode",
            "BACKWARD",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0  # safe_add is BACKWARD compat
    assert "COMPATIBLE" in out

    rc = main(["bump", "--old", str(out_dir / "old.json"), "--new", str(out_dir / "new.json")])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["suggested_bump"] == "minor"

    rc = main(["summary", "--old", str(out_dir / "old.json"), "--new", str(out_dir / "new.json")])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["compatibility"]["BACKWARD"] is True


def test_cli_compat_exits_2_on_incompatible(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "raw"
    main(["simulate", "--mutation", "required_add", "--out-dir", str(out_dir)])
    capsys.readouterr()
    rc = main(
        [
            "compat",
            "--old",
            str(out_dir / "old.json"),
            "--new",
            str(out_dir / "new.json"),
            "--mode",
            "BACKWARD",
        ]
    )
    capsys.readouterr()
    assert rc == 2


def test_cli_compat_unknown_mutation_returns_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["simulate", "--mutation", "NOT_A_REAL_MUTATION", "--out-dir", str(tmp_path)])
    capsys.readouterr()
    assert rc == 2


def test_cli_compat_json_mode_emits_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "raw"
    main(["simulate", "--mutation", "safe_add", "--out-dir", str(out_dir)])
    capsys.readouterr()
    rc = main(
        [
            "compat",
            "--old",
            str(out_dir / "old.json"),
            "--new",
            str(out_dir / "new.json"),
            "--mode",
            "BACKWARD",
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["mode"] == "BACKWARD"
    assert payload["is_compatible"] is True
