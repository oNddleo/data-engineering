"""
Storage layer — EncryptedRecord dataclass and in-memory RecordStore.
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# EncryptedRecord
# ---------------------------------------------------------------------------


@dataclass
class EncryptedRecord:
    """
    A record whose PII columns have been envelope-encrypted.

    Wire format (JSON-serialisable dict):

    .. code-block:: json

        {
          "record_id": "<uuid>",
          "customer_id": "<str>",
          "cmk_id": "<str>",
          "wrapped_dek": "<base64, 64 bytes>",
          "encrypted_columns": {"ssn": "<base64>", ...},
          "plaintext_columns": {"product_id": "...", ...},
          "created_at": "<iso8601>"
        }
    """

    record_id: str
    customer_id: str
    cmk_id: str
    wrapped_dek: str  # base64-encoded 64-byte blob
    encrypted_columns: dict[str, str]  # column -> base64(nonce||ct||mac)
    plaintext_columns: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "customer_id": self.customer_id,
            "cmk_id": self.cmk_id,
            "wrapped_dek": self.wrapped_dek,
            "encrypted_columns": self.encrypted_columns,
            "plaintext_columns": self.plaintext_columns,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EncryptedRecord:
        return cls(
            record_id=data["record_id"],
            customer_id=data["customer_id"],
            cmk_id=data["cmk_id"],
            wrapped_dek=data["wrapped_dek"],
            encrypted_columns=data["encrypted_columns"],
            plaintext_columns=data["plaintext_columns"],
            created_at=data.get("created_at", ""),
        )

    @classmethod
    def from_json(cls, raw: str) -> EncryptedRecord:
        return cls.from_dict(json.loads(raw))


# ---------------------------------------------------------------------------
# RecordStore
# ---------------------------------------------------------------------------


class RecordStore:
    """Simple in-memory store for :class:`EncryptedRecord` objects."""

    def __init__(self) -> None:
        self._records: dict[str, EncryptedRecord] = {}

    def put(self, record: EncryptedRecord) -> None:
        """Insert or replace a record (keyed by ``record_id``)."""
        self._records[record.record_id] = record

    def get(self, record_id: str) -> EncryptedRecord:
        """Retrieve a record by its ``record_id``.

        Raises :class:`KeyError` if the record does not exist.
        """
        return self._records[record_id]

    def list_for_customer(self, customer_id: str) -> list[EncryptedRecord]:
        """Return all records belonging to *customer_id*."""
        return [r for r in self._records.values() if r.customer_id == customer_id]

    def delete(self, record_id: str) -> None:
        """Remove a single record.  Silently ignores missing ids."""
        self._records.pop(record_id, None)

    def delete_all_for_customer(self, customer_id: str) -> int:
        """Delete all records for *customer_id* and return the count."""
        ids = [rid for rid, r in self._records.items() if r.customer_id == customer_id]
        for rid in ids:
            del self._records[rid]
        return len(ids)

    def count(self) -> int:
        """Return total number of stored records."""
        return len(self._records)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode()


def b64_decode(s: str) -> bytes:
    return base64.b64decode(s)


def new_record_id() -> str:
    return str(uuid.uuid4())
