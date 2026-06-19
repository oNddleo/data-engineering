-- =====================================================================
-- postgres-meta init script
-- Default DB `metastore` is created by Postgres image from POSTGRES_DB env.
-- Add Unity Catalog + Airflow DBs as siblings on the same instance to
-- save a container (POC convenience — split per service in production).
-- =====================================================================

CREATE DATABASE ucatalog;
CREATE DATABASE airflow;

-- Grant the bootstrap user full access to all three DBs.
GRANT ALL PRIVILEGES ON DATABASE metastore TO metauser;
GRANT ALL PRIVILEGES ON DATABASE ucatalog  TO metauser;
GRANT ALL PRIVILEGES ON DATABASE airflow   TO metauser;
