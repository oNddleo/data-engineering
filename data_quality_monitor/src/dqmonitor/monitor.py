"""QualityMonitor: orchestrates validator + gate + audit log for streaming batches."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from dqmonitor.audit import AuditLog, ValidationRun
from dqmonitor.gate import QualityGate
from dqmonitor.validator import ValidationResult, Validator

if TYPE_CHECKING:
    from dqmonitor.expectations import ExpectationSuite


class QualityMonitor:
    """High-level orchestrator for batch data quality checks.

    Parameters
    ----------
    suite:
        The :class:`~dqmonitor.expectations.ExpectationSuite` whose rules are
        applied to each batch.
    gate:
        Optional :class:`~dqmonitor.gate.QualityGate`.  If omitted a default
        gate (threshold=0.95) is created.
    audit_log:
        Optional :class:`~dqmonitor.audit.AuditLog`.  If omitted no audit
        records are persisted.
    """

    def __init__(
        self,
        suite: ExpectationSuite,
        gate: QualityGate | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self._suite = suite
        self._gate = gate if gate is not None else QualityGate()
        self._audit_log = audit_log
        self._validator = Validator(list(suite.rules))

    @property
    def suite(self) -> ExpectationSuite:
        return self._suite

    @property
    def gate(self) -> QualityGate:
        return self._gate

    @property
    def audit_log(self) -> AuditLog | None:
        return self._audit_log

    def process_batch(
        self,
        batch: list[dict[str, object]],
        suite_name: str = "",
    ) -> ValidationResult:
        """Validate *batch*, update the gate, and write an audit entry.

        Parameters
        ----------
        batch:
            List of records (dicts) to validate.
        suite_name:
            Override label stored in the audit entry.  Defaults to
            ``self.suite.name``.

        Returns
        -------
        ValidationResult
            The result of running all rules in the suite against *batch*.
        """
        # Re-sync rules in case the suite was mutated after __init__
        self._validator = Validator(list(self._suite.rules))

        result = self._validator.validate(batch)
        gate_open = self._gate.update(result.pass_rate)
        gate_status = "open" if gate_open else "blocked"

        if self._audit_log is not None:
            run = ValidationRun(
                run_id=str(uuid.uuid4()),
                suite_name=suite_name or self._suite.name,
                timestamp=ValidationRun.now_iso(),
                pass_rate=result.pass_rate,
                total=result.total,
                failed=result.failed,
                gate_status=gate_status,
            )
            self._audit_log.append(run)

        return result
