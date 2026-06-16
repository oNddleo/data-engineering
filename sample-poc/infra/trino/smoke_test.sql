-- Phase 1 acceptance smoke test.
-- Proves: Trino reaches the Iceberg REST catalog, and a write physically lands
-- Parquet + metadata under s3://warehouse in MinIO.
CREATE SCHEMA IF NOT EXISTS iceberg.demo;
CREATE TABLE IF NOT EXISTS iceberg.demo.smoke (id integer, note varchar);
INSERT INTO iceberg.demo.smoke VALUES (1, 'phase-1 ok');
SELECT count(*) AS rows FROM iceberg.demo.smoke;
