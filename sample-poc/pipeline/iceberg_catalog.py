"""PyIceberg RestCatalog client wired to Lakekeeper + MinIO.

Centralized so every phase (ingest, transform) builds the catalog identically.
Writes go through PyIceberg because no production pure-Rust Iceberg write path
exists in 2026 — Polars/DataFusion handle reads/transforms, PyIceberg the writes.
"""
from __future__ import annotations

import pyarrow as pa
from pyiceberg.catalog.rest import RestCatalog
from pyiceberg.table import Table

import settings


def get_catalog() -> RestCatalog:
    return RestCatalog(
        name="lakekeeper",
        **{
            "uri": settings.CATALOG_URI,
            "warehouse": settings.CATALOG_WAREHOUSE,
            **settings.s3_properties(),
        },
    )


def ensure_namespace(catalog: RestCatalog, namespace: str) -> None:
    if (namespace,) not in catalog.list_namespaces():
        catalog.create_namespace(namespace)


def ensure_table(catalog: RestCatalog, identifier: str, arrow_schema: pa.Schema) -> Table:
    """Create the table from an Arrow schema if absent; return it either way."""
    if catalog.table_exists(identifier):
        return catalog.load_table(identifier)
    return catalog.create_table(identifier, schema=arrow_schema)
