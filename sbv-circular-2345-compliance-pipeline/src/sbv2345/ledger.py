"""Hash-chained append-only audit ledger + daily Merkle seal.

Each :class:`SealedAuditRecord` stores:

* ``sequence_number`` — 1-indexed position in the chain.
* ``prev_hash`` — the previous record's ``record_hash``, or
  :data:`AuditLedger.GENESIS_HASH` for sequence number 1.
* The :class:`AuditEvent` payload itself.
* ``sealed_at`` — wall-clock time at append.
* ``record_hash`` — SHA-256 of a canonical
  ``prev_hash || sequence_number || canonical(event) || sealed_at``
  encoding.

Tampering with any record breaks the chain: the modified record's
hash no longer matches what's stored, and every subsequent record's
``prev_hash`` is also wrong. :meth:`AuditLedger.verify` walks the
chain and raises :class:`TamperDetected` on the first mismatch.

A daily seal (:class:`DailySeal`) is the Merkle root over all the
``record_hash`` values whose ``event.txn.occurred_at.date()`` equals
the seal day, in chain order. The root is what gets submitted to
SBV in monthly compliance dossiers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sbv2345.merkle import merkle_root

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from datetime import date, datetime

    from sbv2345.schema import AuditEvent


class TamperDetected(Exception):
    """Raised when chain verification finds a hash mismatch."""

    def __init__(self, sequence_number: int, reason: str) -> None:
        super().__init__(f"tamper at sequence={sequence_number}: {reason}")
        self.sequence_number = sequence_number
        self.reason = reason


def _canonical_event(event: AuditEvent) -> str:
    """Stable JSON encoding of an AuditEvent for hashing."""
    txn = event.txn
    payload = {
        "txn_id": txn.txn_id,
        "initiator_account": txn.initiator_account,
        "beneficiary_account": txn.beneficiary_account,
        "amount_vnd": txn.amount_vnd,
        "channel": txn.channel.value,
        "occurred_at": txn.occurred_at.isoformat(),
        "auth_method": txn.auth_method.value,
        "biometric_method": None if txn.biometric_method is None else txn.biometric_method.value,
        "cross_border": txn.cross_border,
        "initiator_bank_bin": txn.initiator_bank_bin,
        "beneficiary_bank_bin": txn.beneficiary_bank_bin,
        "triggered_kinds": [t.value for t in event.triggered_kinds],
        "legal_bases": list(event.legal_bases),
        "daily_cumulative_after_vnd": event.daily_cumulative_after_vnd,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_record_hash(
    sequence_number: int,
    prev_hash: str,
    event: AuditEvent,
    sealed_at: datetime,
) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode("ascii"))
    h.update(b"|")
    h.update(sequence_number.to_bytes(8, "big"))
    h.update(b"|")
    h.update(sealed_at.isoformat().encode("utf-8"))
    h.update(b"|")
    h.update(_canonical_event(event).encode("utf-8"))
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class SealedAuditRecord:
    """One immutable row in the hash-chained ledger."""

    sequence_number: int
    prev_hash: str
    event: AuditEvent
    sealed_at: datetime
    record_hash: str


@dataclass(frozen=True, slots=True)
class DailySeal:
    """Merkle root over all records for one calendar day in UTC+7."""

    day: date
    record_count: int
    merkle_root: str
    sealed_at: datetime


class AuditLedger:
    """Append-only, hash-chained, in-memory store of SealedAuditRecords."""

    GENESIS_HASH = "0" * 64

    def __init__(self) -> None:
        self._records: list[SealedAuditRecord] = []

    @property
    def length(self) -> int:
        return len(self._records)

    @property
    def tip_hash(self) -> str:
        return self._records[-1].record_hash if self._records else self.GENESIS_HASH

    def __iter__(self) -> Iterator[SealedAuditRecord]:
        return iter(self._records)

    def records(self) -> list[SealedAuditRecord]:
        return list(self._records)

    # ------------------------------------------------------------- append

    def append(self, event: AuditEvent, *, sealed_at: datetime) -> SealedAuditRecord:
        if sealed_at.tzinfo is None:
            raise ValueError("sealed_at must be timezone-aware")
        seq = len(self._records) + 1
        prev = self.tip_hash
        rec_hash = _compute_record_hash(seq, prev, event, sealed_at)
        rec = SealedAuditRecord(
            sequence_number=seq,
            prev_hash=prev,
            event=event,
            sealed_at=sealed_at,
            record_hash=rec_hash,
        )
        self._records.append(rec)
        return rec

    def append_many(
        self, events: Iterable[AuditEvent], *, sealed_at: datetime
    ) -> list[SealedAuditRecord]:
        out = [self.append(e, sealed_at=sealed_at) for e in events]
        return out

    # -------------------------------------------------------------- verify

    def verify(self) -> None:
        """Walk the chain end-to-end. Raises :class:`TamperDetected` on mismatch."""
        prev = self.GENESIS_HASH
        for i, rec in enumerate(self._records, start=1):
            if rec.sequence_number != i:
                raise TamperDetected(i, f"sequence_number {rec.sequence_number} != expected {i}")
            if rec.prev_hash != prev:
                raise TamperDetected(i, "prev_hash does not match previous record's record_hash")
            expected = _compute_record_hash(
                rec.sequence_number, rec.prev_hash, rec.event, rec.sealed_at
            )
            if rec.record_hash != expected:
                raise TamperDetected(i, "record_hash does not match computed hash")
            prev = rec.record_hash

    # --------------------------------------------------------------- query

    def query(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        account: str | None = None,
        triggered_kind: str | None = None,
    ) -> list[SealedAuditRecord]:
        out: list[SealedAuditRecord] = []
        for r in self._records:
            t = r.event.txn
            if since is not None and t.occurred_at < since:
                continue
            if until is not None and t.occurred_at > until:
                continue
            if account is not None and t.initiator_account != account:
                continue
            if triggered_kind is not None and not any(
                k.value == triggered_kind for k in r.event.triggered_kinds
            ):
                continue
            out.append(r)
        return out

    # -------------------------------------------------------- daily Merkle

    def seal_day(self, day: date, *, sealed_at: datetime) -> DailySeal:
        if sealed_at.tzinfo is None:
            raise ValueError("sealed_at must be timezone-aware")
        day_records = [r for r in self._records if r.event.txn.occurred_at.date() == day]
        leaves = [r.record_hash for r in day_records]
        return DailySeal(
            day=day,
            record_count=len(day_records),
            merkle_root=merkle_root(leaves),
            sealed_at=sealed_at,
        )


__all__ = [
    "AuditLedger",
    "DailySeal",
    "SealedAuditRecord",
    "TamperDetected",
]
