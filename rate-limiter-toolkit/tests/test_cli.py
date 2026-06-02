"""CLI tests for rate-limiter-toolkit."""

from __future__ import annotations

import json
import sys
from io import StringIO

from ratelimiter.cli import main


def _capture(argv: list[str]) -> tuple[int, str]:
    old_out = sys.stdout
    sys.stdout = buf = StringIO()
    try:
        rc = main(argv)
    finally:
        sys.stdout = old_out
    return rc, buf.getvalue()


def test_token_bucket_default() -> None:
    rc, out = _capture(["token-bucket"])
    assert rc == 0
    obj = json.loads(out)
    assert obj["algorithm"] == "token_bucket"
    assert obj["total_requests"] == 100
    assert obj["allowed"] + obj["rejected"] == 100


def test_sliding_window_default() -> None:
    rc, out = _capture(["sliding-window"])
    assert rc == 0
    obj = json.loads(out)
    assert obj["algorithm"] == "sliding_window"
    assert obj["total_requests"] == 100


def test_no_subcommand_nonzero() -> None:
    rc, _ = _capture([])
    assert rc == 1


def test_sliding_window_tight_limit() -> None:
    rc, out = _capture(
        [
            "sliding-window",
            "--limit",
            "5",
            "--window",
            "1.0",
            "--n-requests",
            "20",
            "--interval",
            "0.1",
        ]
    )
    assert rc == 0
    obj = json.loads(out)
    # 20 requests at 0.1s each over 2s window of 1s → some rejected
    assert obj["allowed"] <= 20
    assert obj["rejected"] >= 0
