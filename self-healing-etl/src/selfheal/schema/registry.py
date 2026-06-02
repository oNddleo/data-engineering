"""In-memory versioned schema registry (JSON-serializable)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class SchemaEntry:
    """A single versioned schema snapshot."""

    version: int
    schema: dict[str, str]
    registered_at: str  # ISO-8601
    is_active: bool = True

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "version": self.version,
            "schema": dict(self.schema),
            "registered_at": self.registered_at,
            "is_active": self.is_active,
        }


class SchemaRegistry:
    """In-memory registry keyed by *source_name*.

    Each source maintains an ordered list of :class:`SchemaEntry` objects.
    The most-recently added active entry is the *current* schema.
    """

    def __init__(self) -> None:
        self._store: dict[str, list[SchemaEntry]] = {}

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def register(self, source_name: str, schema: dict[str, str]) -> SchemaEntry:
        """Register *schema* for *source_name* and return the new entry."""
        history = self._store.setdefault(source_name, [])
        version = (history[-1].version + 1) if history else 1
        entry = SchemaEntry(
            version=version,
            schema=dict(schema),
            registered_at=datetime.now(timezone.utc).isoformat(),
        )
        history.append(entry)
        return entry

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_active(self, source_name: str) -> SchemaEntry | None:
        """Return the current active schema entry, or *None* if not found."""
        history = self._store.get(source_name)
        if not history:
            return None
        # Last active entry wins.
        for entry in reversed(history):
            if entry.is_active:
                return entry
        return None

    def get_history(self, source_name: str) -> list[SchemaEntry]:
        """Return all schema entries for *source_name*, oldest first."""
        return list(self._store.get(source_name, []))

    def sources(self) -> list[str]:
        """Return all registered source names."""
        return list(self._store.keys())

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Dump the entire registry to a JSON string."""
        data: dict[str, list[dict[str, object]]] = {
            name: [e.to_dict() for e in entries] for name, entries in self._store.items()
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> SchemaRegistry:
        """Reconstruct a registry from the JSON produced by :meth:`to_json`."""
        data: dict[str, list[dict[str, object]]] = json.loads(raw)
        reg = cls()
        for name, entries in data.items():
            reg._store[name] = [
                SchemaEntry(
                    version=int(e["version"]),  # type: ignore[call-overload]
                    schema=dict(e["schema"]),  # type: ignore[call-overload]
                    registered_at=str(e["registered_at"]),
                    is_active=bool(e["is_active"]),
                )
                for e in entries
            ]
        return reg
