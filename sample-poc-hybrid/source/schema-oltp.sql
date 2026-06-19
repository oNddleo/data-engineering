-- =====================================================================
-- OLTP devices source schema — postgres-oltp database `devices`
-- Loaded by source/seed-oltp.py (idempotent: TRUNCATE before seed).
-- =====================================================================

CREATE TABLE IF NOT EXISTS locations (
    location_id   SMALLINT      PRIMARY KEY,
    city          TEXT          NOT NULL,
    district      TEXT,
    lat           DOUBLE PRECISION NOT NULL,
    lon           DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    device_id     TEXT          PRIMARY KEY,            -- dev-NNNN
    model         TEXT          NOT NULL,
    owner_org     TEXT          NOT NULL,
    install_date  DATE          NOT NULL,
    fw_version    TEXT          NOT NULL DEFAULT '1.0.0'
);

CREATE TABLE IF NOT EXISTS device_location (
    device_id     TEXT          NOT NULL REFERENCES devices(device_id)   ON DELETE CASCADE,
    location_id   SMALLINT      NOT NULL REFERENCES locations(location_id) ON DELETE RESTRICT,
    assigned_from DATE          NOT NULL,
    PRIMARY KEY (device_id, location_id, assigned_from)
);

CREATE INDEX IF NOT EXISTS ix_device_location_device ON device_location (device_id);
