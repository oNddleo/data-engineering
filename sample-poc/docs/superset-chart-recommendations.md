# Superset Chart Recommendations

Maps each gold mart (and silver source) to the Superset chart type that fits its grain.

## Gold marts → charts

### 1. `daily_revenue` — (order_date, revenue, orders, avg_order_value)
Time series, one row per day. Best for trend dashboards.

| Chart | Metric(s) | Why |
|-------|-----------|-----|
| **Time-series Line Chart** | `revenue` over `order_date` | Primary revenue trend |
| **Time-series Bar Chart** | `orders` over `order_date` | Daily order volume |
| **Mixed / Dual-axis Time-series** | `revenue` (line) + `orders` (bar) | Correlate value vs volume on one panel |
| **Big Number with Trendline** | `SUM(revenue)`, `AVG(avg_order_value)` | KPI tiles at top of dashboard |
| **Area Chart** | `revenue` cumulative | Show running total / momentum |

### 2. `revenue_by_category` — (category, revenue)
Categorical, low cardinality (~handful of categories).

| Chart | Metric(s) | Why |
|-------|-----------|-----|
| **Bar Chart (horizontal)** | `revenue` by `category` | Ranked comparison — clearest for categories |
| **Pie / Donut Chart** | `revenue` share by `category` | Part-to-whole, only if ≤6 categories |
| **Treemap** | `revenue` by `category` | Alternative part-to-whole, scales better |

### 3. `top_customers` — (customer_id, name, country, lifetime_value)
Ranked entity list + a geo dimension.

| Chart | Metric(s) | Why |
|-------|-----------|-----|
| **Bar Chart (horizontal, sorted)** | `lifetime_value` by `name`, top N | Leaderboard of best customers |
| **Table** | all columns, sorted by `lifetime_value` | Drill detail, sortable/searchable |
| **Bar Chart / World Map** | `SUM(lifetime_value)` by `country` | Revenue concentration by country |

### 4. `order_status_funnel` — (status, orders)
Categorical stages of order lifecycle.

| Chart | Metric(s) | Why |
|-------|-----------|-----|
| **Funnel Chart** | `orders` by `status` | Designed exactly for stage drop-off |
| **Bar Chart** | `orders` by `status` | Simple fallback if stages aren't ordered |
| **Big Number** | `SUM(orders)` | Total orders KPI |

## Silver sources → optional supporting charts
Use only if you want raw exploration beyond the marts.

| Source | Chart | Use |
|--------|-------|-----|
| `customers` | Bar / World Map by `country` | Customer count distribution |
| `products` | Histogram of `price`, Bar by `category` | Price spread, catalog mix |
| `order_items` | Histogram of `quantity` | Basket-size distribution |
| `orders` | Time-series by `order_ts` | Raw order cadence |

## Suggested dashboard layout
1. **Top row (KPIs):** Big Number — Total Revenue, Total Orders, Avg Order Value (from `daily_revenue`).
2. **Trend row:** Dual-axis Time-series — revenue + orders.
3. **Mix row:** Bar `revenue_by_category` | Funnel `order_status_funnel`.
4. **Customer row:** Top-N Bar `top_customers` | Country map.

## Notes
- All gold marts are pre-aggregated, so in Superset use metric `SUM(revenue)` / `MAX` with no further GROUP BY needed beyond the dimension shown.
- For time-series charts set `order_date` / `order_ts` as the Time column and pick a Day grain.
- Pie/Donut only when categories ≤ 6; otherwise prefer Bar/Treemap.
