"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scdkit.cli import main
from scdkit.detect import detect
from scdkit.schema import ChangeKind
from scdkit.simulator import generate_pair

from ._fixtures import DEFAULT_TS


def test_simulate_deterministic_with_seed():
    a = generate_pair(n_entities=20, seed=42)
    b = generate_pair(n_entities=20, seed=42)
    assert a == b


def test_simulate_emits_n_entities_before():
    before, after = generate_pair(n_entities=30, seed=1)
    assert len(before) == 30


def test_simulate_insert_fraction_observable():
    before, after = generate_pair(
        n_entities=100,
        insert_fraction=0.10,
        delete_fraction=0.0,
        update_fraction=0.0,
        seed=2,
    )
    changes = detect(before, after, as_of=DEFAULT_TS)
    n_inserts = sum(1 for c in changes if c.kind is ChangeKind.INSERT)
    assert n_inserts == 10


def test_simulate_delete_fraction_observable():
    before, after = generate_pair(
        n_entities=100,
        insert_fraction=0.0,
        delete_fraction=0.05,
        update_fraction=0.0,
        seed=3,
    )
    changes = detect(before, after, as_of=DEFAULT_TS)
    n_deletes = sum(1 for c in changes if c.kind is ChangeKind.DELETE)
    assert n_deletes == 5


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate_pair(n_entities=0)
    with pytest.raises(ValueError):
        generate_pair(insert_fraction=1.5)


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "slowly-changing-dimensions-toolkit" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    rc = main(["simulate", "--entities", "20", "--seed", "0", "--out-dir", str(out_dir)])
    assert rc == 0
    assert (out_dir / "before.jsonl").is_file()
    assert (out_dir / "after.jsonl").is_file()
    capsys.readouterr()

    changes_path = tmp_path / "changes.jsonl"
    rc = main(
        [
            "detect",
            "--before",
            str(out_dir / "before.jsonl"),
            "--after",
            str(out_dir / "after.jsonl"),
            "--as-of",
            "2026-05-17T09:00:00+07:00",
            "--output",
            str(changes_path),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "INSERT" in out

    for scd_type in ("TYPE_1", "TYPE_2", "TYPE_3", "TYPE_4", "TYPE_6"):
        out_path = tmp_path / f"{scd_type.lower()}.jsonl"
        rc = main(
            [
                "apply",
                "--type",
                scd_type,
                "--changes",
                str(changes_path),
                "--tracked-attrs",
                "shop_name,tier",
                "--output",
                str(out_path),
            ]
        )
        assert rc == 0
        assert out_path.is_file()
        capsys.readouterr()

    rc = main(
        [
            "summary",
            "--before",
            str(out_dir / "before.jsonl"),
            "--after",
            str(out_dir / "after.jsonl"),
            "--as-of",
            "2026-05-17T09:00:00+07:00",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_before"] == 20
    assert "by_kind" in payload


def test_cli_history_known_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    main(["simulate", "--entities", "20", "--seed", "0", "--out-dir", str(out_dir)])
    changes_path = tmp_path / "changes.jsonl"
    main(
        [
            "detect",
            "--before",
            str(out_dir / "before.jsonl"),
            "--after",
            str(out_dir / "after.jsonl"),
            "--as-of",
            "2026-05-17T09:00:00+07:00",
            "--output",
            str(changes_path),
        ]
    )
    capsys.readouterr()

    rc = main(["history", "--changes", str(changes_path), "--natural-key", "S-000000"])
    capsys.readouterr()
    # Either exit 0 (history exists) or 1 (no history) — both are legal.
    assert rc in (0, 1)


def test_cli_history_unknown_key_returns_1(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_dir = tmp_path / "raw"
    main(["simulate", "--entities", "5", "--seed", "0", "--out-dir", str(out_dir)])
    changes_path = tmp_path / "changes.jsonl"
    main(
        [
            "detect",
            "--before",
            str(out_dir / "before.jsonl"),
            "--after",
            str(out_dir / "after.jsonl"),
            "--as-of",
            "2026-05-17T09:00:00+07:00",
            "--output",
            str(changes_path),
        ]
    )
    capsys.readouterr()

    rc = main(["history", "--changes", str(changes_path), "--natural-key", "DOES-NOT-EXIST"])
    capsys.readouterr()
    assert rc == 1
