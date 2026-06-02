"""CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "vncal.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    out = _run_cli("info")
    assert out.returncode == 0
    assert "vn-business-day-calendar" in out.stdout


def test_cli_holidays_2026():
    r = _run_cli("holidays", "--year", "2026")
    assert r.returncode == 0
    assert "Tết Dương Lịch" in r.stdout
    assert "Quốc Khánh" in r.stdout


def test_cli_holidays_range(tmp_path: Path) -> None:
    out_path = tmp_path / "holidays.jsonl"
    r = _run_cli("holidays", "--year", "2024", "--year-to", "2026", "--output", str(out_path))
    assert r.returncode == 0
    assert out_path.exists()
    lines = [line for line in out_path.read_text().splitlines() if line.strip()]
    assert len(lines) >= 33  # 3 years × ~11 holidays


def test_cli_is_business_day_returns_0_on_workday():
    r = _run_cli("is-business-day", "--date", "2026-05-18")
    assert r.returncode == 0


def test_cli_is_business_day_returns_1_on_holiday():
    r = _run_cli("is-business-day", "--date", "2026-02-17")
    assert r.returncode == 1


def test_cli_add():
    r = _run_cli("add", "--date", "2026-05-18", "--days", "5")
    assert r.returncode == 0
    assert "2026-05-25" in r.stdout


def test_cli_between():
    r = _run_cli("between", "--start", "2026-05-18", "--end", "2026-05-25")
    assert r.returncode == 0
    assert r.stdout.strip() == "5"


def test_cli_fiscal_year_calendar():
    r = _run_cli("fiscal-year", "--date", "2026-05-18")
    assert r.returncode == 0
    assert "FY2026" in r.stdout
    assert "365 days" in r.stdout


def test_cli_fiscal_year_april_march():
    r = _run_cli("fiscal-year", "--date", "2026-05-18", "--april-march")
    assert r.returncode == 0
    assert "FY2026-27" in r.stdout


def test_cli_summary():
    r = _run_cli("summary", "--year", "2026")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["year"] == 2026
    assert payload["n_calendar_days"] == 365
    # 11 base holidays + 1 compensation (Giỗ Tổ on Sun) = 12 in 2026.
    assert payload["n_holidays"] >= 11
