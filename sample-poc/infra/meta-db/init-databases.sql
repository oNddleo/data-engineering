-- Runs once on first init of the shared meta-db Postgres.
-- Creates the logical databases used by internal services so we do NOT
-- spawn a separate Postgres container per tool (Lakekeeper / Airflow / Superset).

CREATE DATABASE lakekeeper;
CREATE DATABASE airflow;
CREATE DATABASE superset;
