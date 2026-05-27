"""PipelineRunner: orchestrate extract → detect → heal → load."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selfheal.alerts.alerter import ConsoleAlerter
    from selfheal.quarantine.store import QuarantineStore
    from selfheal.schema.drift import DriftEvent
    from selfheal.schema.registry import SchemaRegistry


@dataclass
class RunResult:
    """Summary of a single pipeline run."""

    loaded: int
    quarantined: int
    drift_events: list[DriftEvent] = field(default_factory=list)
    healed: int = 0
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class PipelineRunner:
    """Orchestrate a single batch through the self-healing ETL pipeline.

    Parameters
    ----------
    registry:
        Schema registry — must already contain an active schema for
        *source_name*.
    source_name:
        Logical name of the data source.
    quarantine_store:
        Where bad records are sent.
    alerter:
        Optional :class:`~selfheal.alerts.alerter.ConsoleAlerter`.
    """

    def __init__(
        self,
        registry: SchemaRegistry,
        source_name: str,
        quarantine_store: QuarantineStore,
        alerter: ConsoleAlerter | None = None,
    ) -> None:
        self._registry = registry
        self._source_name = source_name
        self._quarantine = quarantine_store
        self._alerter = alerter

    # ------------------------------------------------------------------

    def run(self, records: list[dict[str, object]]) -> RunResult:
        """Process *records* and return a :class:`RunResult`.

        Steps:
        1. Infer batch schema.
        2. Detect drift vs. current registered schema.
        3. If drift: apply healing per record; unrecoverable → quarantine.
        4. Return summary.
        """
        from selfheal.healing.strategies import HealingEngine  # noqa: PLC0415
        from selfheal.schema.drift import DriftDetector  # noqa: PLC0415

        run_id = str(uuid.uuid4())
        active_entry = self._registry.get_active(self._source_name)

        # No schema yet — bootstrap from the batch and load everything.
        if active_entry is None:
            batch_schema = DriftDetector.infer_schema(records)
            self._registry.register(self._source_name, batch_schema)
            return RunResult(
                loaded=len(records),
                quarantined=0,
                drift_events=[],
                healed=0,
                run_id=run_id,
            )

        batch_schema = DriftDetector.infer_schema(records)
        detector = DriftDetector(active_entry.schema)
        drift_events = detector.detect(batch_schema)

        if not drift_events:
            return RunResult(
                loaded=len(records),
                quarantined=0,
                drift_events=[],
                healed=0,
                run_id=run_id,
            )

        # We have drift — alert and attempt healing.
        if self._alerter:
            self._alerter.alert_drift_detected(self._source_name, drift_events)

        engine = HealingEngine(self._registry, self._source_name)
        loaded = 0
        healed = 0
        strategy_counts: dict[str, int] = {}

        for record in records:
            result = engine.heal(record, drift_events)
            if result.healed:
                loaded += 1
                healed += 1
                if result.strategy_used:
                    strategy_counts[result.strategy_used] = (
                        strategy_counts.get(result.strategy_used, 0) + 1
                    )
            else:
                self._quarantine.add(
                    record,
                    error_type="heal_failed",
                    error_detail=result.failure_reason or "unknown",
                    run_id=run_id,
                )
                if self._alerter:
                    self._alerter.alert_quarantine(self._source_name, 1, "heal_failed")

        # Emit healing summary alerts.
        if self._alerter:
            for strategy, count in strategy_counts.items():
                self._alerter.alert_healing_applied(self._source_name, strategy, count)

        quarantined = len(records) - loaded
        run_result = RunResult(
            loaded=loaded,
            quarantined=quarantined,
            drift_events=drift_events,
            healed=healed,
            run_id=run_id,
        )

        if self._alerter:
            self._alerter.alert_run_complete(self._source_name, run_result)

        return run_result
