-- Trino validation + demo queries over the lakehouse.
-- Run via: make trino-cli   (then paste), or as Superset chart sources.

-- 1) Catalog reachable + medallion namespaces present
SHOW SCHEMAS FROM iceberg;

-- 2) Bronze row counts (raw, append-only — may exceed source after appends)
SELECT 'customers'   AS t, count(*) c FROM iceberg.bronze.customers
UNION ALL SELECT 'products',    count(*) FROM iceberg.bronze.products
UNION ALL SELECT 'orders',      count(*) FROM iceberg.bronze.orders
UNION ALL SELECT 'order_items', count(*) FROM iceberg.bronze.order_items;

-- 3) Gold marts (dashboard sources)
SELECT * FROM iceberg.gold.daily_revenue ORDER BY order_date;
SELECT * FROM iceberg.gold.revenue_by_category ORDER BY revenue DESC;
SELECT * FROM iceberg.gold.top_customers ORDER BY lifetime_value DESC LIMIT 20;
SELECT * FROM iceberg.gold.order_status_funnel ORDER BY orders DESC;

-- 4) RECONCILIATION canary: gold daily_revenue total must equal raw line revenue
--    computed straight from silver. Compared with a 1-cent epsilon (Float64 sums
--    drift); `reconciled` must be true. Any false = a dedup/type bug upstream.
SELECT
  gold_total,
  silver_line_total,
  abs(gold_total - silver_line_total)        AS diff,
  abs(gold_total - silver_line_total) < 0.01 AS reconciled
FROM (
  SELECT
    (SELECT sum(revenue) FROM iceberg.gold.daily_revenue)                  AS gold_total,
    (SELECT sum(quantity * unit_price) FROM iceberg.silver.order_items)    AS silver_line_total
);
