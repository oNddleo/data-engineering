"""ConsoleAlerter: structured console output for pipeline events."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import io

    from ..pipeline.runner import RunResult
    from ..schema.drift import DriftEvent

# Severity → ANSI colour codes (works in any ANSI-capable terminal).
_COLOURS: dict[str, str] = {
    "high": "\033[91m",  # bright red
    "medium": "\033[93m",  # bright yellow
    "low": "\033[96m",  # bright cyan
    "info": "\033[92m",  # bright green
    "reset": "\033[0m",
}


def _coloured(text: str, colour: str) -> str:
    code = _COLOURS.get(colour, "")
    reset = _COLOURS["reset"]
    return f"{code}{text}{reset}"


class ConsoleAlerter:
    """Emit structured, human-readable pipeline alerts to stdout/stderr.

    Parameters
    ----------
    stream:
        Where to write alerts.  Defaults to ``sys.stdout``.
    use_colour:
        Emit ANSI colour codes.  Defaults to ``True``.
    """

    def __init__(
        self,
        stream: object = None,
        use_colour: bool = True,
    ) -> None:
        self._stream: io.TextIOBase = stream or sys.stdout  # type: ignore[assignment]
        self._use_colour = use_colour

    # ------------------------------------------------------------------

    def _write(self, line: str) -> None:
        print(line, file=self._stream)

    def _fmt(self, text: str, colour: str) -> str:
        if self._use_colour:
            return _coloured(text, colour)
        return text

    def _ts(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------------------
    # Public alert methods
    # ------------------------------------------------------------------

    def alert_drift_detected(self, source_name: str, events: list[DriftEvent]) -> None:
        """Emit an alert for one or more drift events."""
        ts = self._ts()
        header = self._fmt(
            f"[{ts}] DRIFT DETECTED on '{source_name}' ({len(events)} event(s))",
            "medium",
        )
        self._write(header)
        for ev in events:
            line = (
                f"  • [{ev.severity.upper()}] {ev.drift_type.value}"
                f" column={ev.column!r}"
                f" old={ev.old_type!r} new={ev.new_type!r}"
            )
            self._write(self._fmt(line, ev.severity))

    def alert_healing_applied(
        self,
        source_name: str,
        strategy: str,
        count: int,
    ) -> None:
        """Emit an alert when a healing strategy was applied."""
        ts = self._ts()
        msg = f"[{ts}] HEALED '{source_name}' — strategy={strategy!r}" f" records_healed={count}"
        self._write(self._fmt(msg, "info"))

    def alert_quarantine(
        self,
        source_name: str,
        count: int,
        error_type: str,
    ) -> None:
        """Emit an alert when records are quarantined."""
        ts = self._ts()
        msg = (
            f"[{ts}] QUARANTINE '{source_name}' — {count} record(s)"
            f" quarantined error_type={error_type!r}"
        )
        self._write(self._fmt(msg, "high"))

    def alert_run_complete(self, source_name: str, result: RunResult) -> None:
        """Emit a summary alert at the end of a pipeline run."""
        ts = self._ts()
        msg = (
            f"[{ts}] RUN COMPLETE '{source_name}'"
            f" loaded={result.loaded}"
            f" quarantined={result.quarantined}"
            f" drift_events={len(result.drift_events)}"
            f" healed={result.healed}"
        )
        self._write(self._fmt(msg, "info"))
