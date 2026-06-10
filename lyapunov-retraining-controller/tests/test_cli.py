"""CLI smoke tests."""

import pytest

from lrc.cli import main


def test_info(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "lyapunov-retraining-controller" in out
    assert "benchmark" in out


def test_run_lyapunov(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--steps", "30", "--seed", "1"]) == 0
    out = capsys.readouterr().out
    assert "lyapunov" in out
    assert "mean V" in out


def test_run_fixed_with_shock(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "run",
            "--controller",
            "fixed",
            "--period",
            "5",
            "--alpha",
            "0.5",
            "--drift",
            "shock",
            "--shock-at",
            "10",
            "--steps",
            "40",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "fixed(k=5" in out


def test_run_never_controller(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--controller", "never", "--steps", "10"]) == 0
    assert "never" in capsys.readouterr().out


def test_benchmark_small(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["benchmark", "--steps", "20", "--seeds", "2"]) == 0
    out = capsys.readouterr().out
    assert "controller" in out
    assert "lyapunov" in out
    assert "never" in out


def test_requires_subcommand() -> None:
    with pytest.raises(SystemExit):
        main([])
