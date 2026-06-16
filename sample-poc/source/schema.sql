-- Source OLTP schema: e-commerce domain (synthetic).
-- Idempotent DDL. Every incrementally-extracted table carries created_at +
-- updated_at; updated_at is indexed so watermark extraction (Phase 3) is cheap.

CREATE TABLE IF NOT EXISTS customers (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT        NOT NULL,
    email       TEXT        NOT NULL,
    country     TEXT        NOT NULL,
    segment     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT          NOT NULL,
    category    TEXT          NOT NULL,
    price       NUMERIC(10,2) NOT NULL,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id  BIGINT      NOT NULL REFERENCES customers(id),
    status       TEXT        NOT NULL,
    order_ts     TIMESTAMPTZ NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_items (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id    BIGINT        NOT NULL REFERENCES orders(id),
    product_id  BIGINT        NOT NULL REFERENCES products(id),
    quantity    INT           NOT NULL,
    unit_price  NUMERIC(10,2) NOT NULL,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_customers_updated_at   ON customers(updated_at);
CREATE INDEX IF NOT EXISTS idx_products_updated_at    ON products(updated_at);
CREATE INDEX IF NOT EXISTS idx_orders_updated_at      ON orders(updated_at);
CREATE INDEX IF NOT EXISTS idx_order_items_updated_at ON order_items(updated_at);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id     ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id   ON order_items(order_id);
