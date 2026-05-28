"""AuditLog: records every query with epsilon projections from all three accountants."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from privledger.mechanisms import GaussianMechanism, LaplaceMechanism

if TYPE_CHECKING:
    from pathlib import Path

Mechanism = GaussianMechanism | LaplaceMechanism


@dataclass(frozen=True)
class AuditEntry:
    """Immutable record of a single query execution."""

    query_id: str
    dataset: str
    analyst: str
    mechanism_type: str  # "gaussian" or "laplace"
    sensitivity: float
    # Mechanism parameters
    sigma_or_b: float  # sigma for Gaussian, b for Laplace
    # Epsilon projections
    epsilon_basic: float
    epsilon_rdp: float
    epsilon_zcdp: float
    # How much tighter is RDP vs basic?
    savings_vs_basic: float  # epsilon_basic - epsilon_rdp  (>0 means RDP is tighter)
    delta: float
    timestamp: str  # ISO-8601

    @staticmethod
    def create(
        *,
        query_id: str,
        dataset: str,
        analyst: str,
        mechanism: Mechanism,
        delta: float,
        timestamp: str | None = None,
    ) -> AuditEntry:
        """Construct an AuditEntry from a mechanism."""
        ts = timestamp or datetime.now(tz=UTC).isoformat()

        if isinstance(mechanism, GaussianMechanism):
            mtype = "gaussian"
            param = mechanism.sigma
            eps_basic = mechanism.dp_epsilon(delta)
            eps_rdp = mechanism.rdp_to_dp_epsilon(delta)
            eps_zcdp = mechanism.dp_epsilon(delta)  # uses zCDP Balle conversion
        else:
            mtype = "laplace"
            param = mechanism.b
            eps_basic = mechanism.dp_epsilon()
            eps_rdp = mechanism.dp_epsilon()  # Laplace: RDP equals pure DP for our bound
            eps_zcdp = mechanism.dp_epsilon()  # same

        savings = eps_basic - eps_rdp

        return AuditEntry(
            query_id=query_id,
            dataset=dataset,
            analyst=analyst,
            mechanism_type=mtype,
            sensitivity=mechanism.sensitivity,
            sigma_or_b=param,
            epsilon_basic=eps_basic,
            epsilon_rdp=eps_rdp,
            epsilon_zcdp=eps_zcdp,
            savings_vs_basic=savings,
            delta=delta,
            timestamp=ts,
        )

    def to_dict(self) -> dict[str, object]:
        """Convert to a plain dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class AuditLog:
    """Append-only log of AuditEntry records with optional file persistence."""

    persist_path: Path | None = None
    _entries: list[AuditEntry] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.persist_path is not None and self.persist_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        dataset: str,
        analyst: str,
        mechanism: Mechanism,
        delta: float,
        query_id: str | None = None,
        timestamp: str | None = None,
    ) -> AuditEntry:
        """Create and store an AuditEntry; return it."""
        qid = query_id or str(uuid.uuid4())
        entry = AuditEntry.create(
            query_id=qid,
            dataset=dataset,
            analyst=analyst,
            mechanism=mechanism,
            delta=delta,
            timestamp=timestamp,
        )
        self._entries.append(entry)
        if self.persist_path is not None:
            self._append_line(entry)
        return entry

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    @property
    def entries(self) -> list[AuditEntry]:
        """Return all entries (newest last)."""
        return list(self._entries)

    def filter(
        self,
        *,
        dataset: str | None = None,
        analyst: str | None = None,
    ) -> list[AuditEntry]:
        """Return entries filtered by dataset and/or analyst."""
        result = self._entries
        if dataset is not None:
            result = [e for e in result if e.dataset == dataset]
        if analyst is not None:
            result = [e for e in result if e.analyst == analyst]
        return list(result)

    def total_savings(self, *, dataset: str | None = None, analyst: str | None = None) -> float:
        """Return sum of savings_vs_basic across filtered entries."""
        return sum(e.savings_vs_basic for e in self.filter(dataset=dataset, analyst=analyst))

    def clear(self) -> None:
        """Remove all in-memory entries and truncate the persist file if set."""
        self._entries = []
        if self.persist_path is not None:
            self.persist_path.write_text("")

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _append_line(self, entry: AuditEntry) -> None:
        assert self.persist_path is not None
        with self.persist_path.open("a", encoding="utf-8") as fh:
            fh.write(entry.to_json() + "\n")

    def _load(self) -> None:
        assert self.persist_path is not None
        for line in self.persist_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            self._entries.append(AuditEntry(**data))
