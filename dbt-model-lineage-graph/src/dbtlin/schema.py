"""dbt lineage schema — Model, Source, and the edges between them.

A dbt project is a DAG where:

* **Models** are SQL files under ``models/`` that produce a table or
  view. They reference upstream nodes via ``{{ ref('model_name') }}``.
* **Sources** are external tables registered in ``sources.yml``.
  Models reference them via ``{{ source('schema_name', 'table_name') }}``.
* **Edges** connect dependent → dependency.

The toolkit doesn't parse YAML — it parses **SQL files**, extracting
``ref`` and ``source`` calls. Sources are inferred from the references
encountered (no manual declaration needed for analysis).

Materialization (table / view / incremental / ephemeral) doesn't
affect lineage — the DAG is the same shape regardless. Production
callers layer materialization info separately if needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NodeKind(str, Enum):
    """Two node types in a dbt DAG."""

    MODEL = "MODEL"
    SOURCE = "SOURCE"


@dataclass(frozen=True, slots=True)
class NodeId:
    """Composite identifier — kind + canonical name.

    For a MODEL the canonical name is the file's basename (without
    ``.sql``). For a SOURCE it's ``"schema.table"``.
    """

    kind: NodeKind
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if self.kind is NodeKind.SOURCE and "." not in self.name:
            raise ValueError(f"source name must be 'schema.table', got {self.name!r}")

    @property
    def label(self) -> str:
        """Readable single-string form for graph rendering."""
        return f"{self.kind.value}:{self.name}"


@dataclass(frozen=True, slots=True)
class Model:
    """One dbt model (a SQL file under ``models/``)."""

    name: str
    sql: str
    # Populated by the parser after construction in practice; held here
    # to keep the data class self-contained.
    refs: tuple[str, ...] = ()
    sources: tuple[tuple[str, str], ...] = ()  # list of (schema, table)
    path: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if "/" in self.name or "\\" in self.name:
            raise ValueError(f"name must be a basename (no path separators), got {self.name!r}")


@dataclass(frozen=True, slots=True)
class Edge:
    """A directed edge ``downstream → upstream``.

    The convention follows dbt: the **downstream** node *uses* the
    upstream. If model A reads from model B, the edge is
    ``A.depends_on = B`` and the directed edge is ``A → B``.
    """

    downstream: NodeId
    upstream: NodeId


@dataclass(frozen=True, slots=True)
class CycleReport:
    """One detected cycle — a closed loop in the DAG."""

    cycle: tuple[NodeId, ...]

    def __post_init__(self) -> None:
        if len(self.cycle) < 2:
            raise ValueError(f"a cycle must have at least 2 nodes, got {len(self.cycle)}")


@dataclass(frozen=True, slots=True)
class ImpactReport:
    """Upstream + downstream impact of one model.

    Used to answer "if I change ``raw_orders``, what breaks?"
    (downstream) or "what feeds into ``dim_customer``?" (upstream).
    """

    target: NodeId
    upstream: tuple[NodeId, ...]
    downstream: tuple[NodeId, ...]

    @property
    def n_total_affected(self) -> int:
        return len(self.upstream) + len(self.downstream)


__all__ = [
    "CycleReport",
    "Edge",
    "ImpactReport",
    "Model",
    "NodeId",
    "NodeKind",
]
