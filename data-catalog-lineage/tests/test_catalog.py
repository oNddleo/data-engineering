"""Tests for the DataCatalog."""

from __future__ import annotations

from datacatalog.catalog import DataCatalog
from datacatalog.schema import Column, ColumnRef, DataSource, LineageEdge, PIICategory, Table


def _demo_catalog() -> DataCatalog:
    catalog = DataCatalog()
    src = DataSource("raw", "Raw DB")
    src.tables = [
        Table(
            "users",
            schema="public",
            columns=[
                Column("user_id", "int"),
                Column("email", "varchar"),
                Column("first_name", "varchar"),
            ],
        ),
    ]
    catalog.register_source(src)
    return catalog


class TestDataCatalog:
    def test_register_source(self) -> None:
        catalog = _demo_catalog()
        assert len(catalog.sources()) == 1

    def test_pii_auto_detected_on_register(self) -> None:
        catalog = _demo_catalog()
        t = catalog.get_table("raw", "public", "users")
        assert t is not None
        email_col = next(c for c in t.columns if c.name == "email")
        assert email_col.pii == PIICategory.EMAIL

    def test_get_table(self) -> None:
        catalog = _demo_catalog()
        t = catalog.get_table("raw", "public", "users")
        assert t is not None
        assert t.name == "users"

    def test_get_table_missing(self) -> None:
        catalog = _demo_catalog()
        assert catalog.get_table("raw", "public", "nonexistent") is None

    def test_get_column(self) -> None:
        catalog = _demo_catalog()
        ref = ColumnRef("raw", "public", "users", "email")
        col = catalog.get_column(ref)
        assert col is not None
        assert col.name == "email"

    def test_pii_report(self) -> None:
        catalog = _demo_catalog()
        pii = catalog.pii_report()
        pii_names = {ref.column for ref, _ in pii}
        assert "email" in pii_names
        assert "first_name" in pii_names

    def test_register_lineage_and_downstream(self) -> None:
        catalog = _demo_catalog()
        src = ColumnRef("raw", "public", "users", "email")
        tgt = ColumnRef("stg", "public", "users_stg", "email")
        catalog.register_lineage([LineageEdge(src, tgt, "j1")])
        downs = catalog.downstream_of(src)
        assert tgt in downs

    def test_register_job(self) -> None:
        catalog = _demo_catalog()
        src = ColumnRef("raw", "public", "users", "email")
        tgt = ColumnRef("stg", "public", "users_stg", "email")
        catalog.register_job("j1", [(src, tgt)])
        assert len(catalog.lineage_graph().edges()) == 1

    def test_search(self) -> None:
        catalog = _demo_catalog()
        results = catalog.search("email")
        assert len(results) >= 1
        assert all("email" in col.name.lower() for _, _, col in results)

    def test_pii_impact_report(self) -> None:
        catalog = _demo_catalog()
        email_ref = ColumnRef("raw", "public", "users", "email")
        stg_ref = ColumnRef("stg", "public", "stg_email", "email")
        catalog.register_lineage([LineageEdge(email_ref, stg_ref, "j1")])
        impact = catalog.pii_impact_report()
        found = {ref: downs for ref, downs in impact if ref == email_ref}
        assert email_ref in found
        assert stg_ref in found[email_ref]
