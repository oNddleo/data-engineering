"""High-level DataCatalog combining asset registry, PII detection, and lineage."""

from __future__ import annotations

from datacatalog.lineage import LineageGraph
from datacatalog.pii import PIIDetector
from datacatalog.schema import (
    Column,
    ColumnRef,
    DataSource,
    LineageEdge,
    PIICategory,
    Table,
)


class DataCatalog:
    """In-memory data catalog.

    Manages:
    - Data sources and their tables/columns
    - PII detection on column names
    - Column-level lineage graph
    """

    def __init__(self) -> None:
        self._sources: dict[str, DataSource] = {}
        self._lineage = LineageGraph()
        self._pii = PIIDetector()

    # ── Asset registration ────────────────────────────────────────────────────

    def register_source(self, source: DataSource) -> None:
        self._sources[source.source_id] = source
        # Auto-detect PII on all columns
        for table in source.tables:
            table.source_id = source.source_id
            for col in table.columns:
                if col.pii == PIICategory.NONE:
                    col.pii = self._pii.detect(col.name, col.sample_values)

    def add_table(self, source_id: str, table: Table) -> None:
        source = self._sources.get(source_id)
        if source is None:
            raise KeyError(f"Unknown source: {source_id!r}")
        table.source_id = source_id
        for col in table.columns:
            if col.pii == PIICategory.NONE:
                col.pii = self._pii.detect(col.name, col.sample_values)
        source.tables.append(table)

    # ── Lineage registration ──────────────────────────────────────────────────

    def register_lineage(self, edges: list[LineageEdge]) -> None:
        self._lineage.add_edges(edges)

    def register_job(
        self,
        job_id: str,
        mappings: list[tuple[ColumnRef, ColumnRef]],
        transform: str = "",
    ) -> None:
        """Register a job's column-level mappings."""
        edges = [LineageEdge(src, tgt, job_id, transform) for src, tgt in mappings]
        self._lineage.add_edges(edges)

    # ── Queries ───────────────────────────────────────────────────────────────

    def sources(self) -> list[DataSource]:
        return list(self._sources.values())

    def get_source(self, source_id: str) -> DataSource | None:
        return self._sources.get(source_id)

    def get_table(self, source_id: str, schema: str, table: str) -> Table | None:
        src = self._sources.get(source_id)
        if src is None:
            return None
        for t in src.tables:
            if t.schema == schema and t.name == table:
                return t
        return None

    def get_column(self, ref: ColumnRef) -> Column | None:
        t = self.get_table(ref.source_id, ref.schema, ref.table)
        if t is None:
            return None
        for c in t.columns:
            if c.name == ref.column:
                return c
        return None

    def pii_report(self) -> list[tuple[ColumnRef, PIICategory]]:
        """All PII columns across all sources."""
        results: list[tuple[ColumnRef, PIICategory]] = []
        for src in self._sources.values():
            for table in src.tables:
                for col in table.columns:
                    if col.pii != PIICategory.NONE:
                        ref = ColumnRef(src.source_id, table.schema, table.name, col.name)
                        results.append((ref, col.pii))
        return results

    def upstream_of(self, ref: ColumnRef) -> list[ColumnRef]:
        return self._lineage.upstream_of(ref)

    def downstream_of(self, ref: ColumnRef) -> list[ColumnRef]:
        return self._lineage.downstream_of(ref)

    def pii_impact_report(self) -> list[tuple[ColumnRef, list[ColumnRef]]]:
        """For each PII column, list all columns it flows into downstream."""
        pii_cols = [ref for ref, _ in self.pii_report()]
        return [(ref, self._lineage.downstream_of(ref)) for ref in pii_cols]

    def lineage_graph(self) -> LineageGraph:
        return self._lineage

    def search(self, query: str) -> list[tuple[str, str, Column]]:
        """Search columns by name substring. Returns (source_id, fqn, Column)."""
        query_lower = query.lower()
        results: list[tuple[str, str, Column]] = []
        for src in self._sources.values():
            for table in src.tables:
                for col in table.columns:
                    if query_lower in col.name.lower():
                        results.append((src.source_id, table.fqn, col))
        return results
