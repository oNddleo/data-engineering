"""Seeded synthetic CSV generator.

Produces realistic-looking VN-flavoured CSVs covering the seven
detected types, with configurable nullability rate and row count.
Used by tests and CLI demos.

Default schema:

| Column        | Type      | Example                  |
| ------------- | --------- | ------------------------ |
| order_id      | INT       | 1, 2, …                  |
| customer_name | STRING    | "Nguyễn Văn A"           |
| email         | STRING    | "user@example.vn"        |
| amount_vnd    | DECIMAL   | "1.500.000,00"           |
| qty           | INT       | 1..10                    |
| is_paid       | BOOL      | "Có" / "Không"           |
| created_date  | DATE      | "17/05/2026"             |
| signed_at     | DATETIME  | "2026-05-17T09:00:00"    |
| note          | STRING    | optional, sometimes empty|

The simulator returns the CSV body as a single ``str``.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

_VN_FIRST_NAMES = (
    "Nguyễn Văn A",
    "Trần Thị B",
    "Lê Văn C",
    "Phạm Thị D",
    "Hoàng Văn E",
    "Đặng Thị F",
    "Bùi Văn G",
    "Vũ Thị H",
)


def generate(
    *,
    n_rows: int = 100,
    null_fraction: float = 0.05,
    delimiter: str = ",",
    seed: int = 0,
) -> str:
    """Generate a synthetic CSV with the default schema."""
    if not 0 <= null_fraction <= 1:
        raise ValueError("null_fraction must be in [0, 1]")
    if n_rows < 0:
        raise ValueError("n_rows must be >= 0")
    if not delimiter:
        raise ValueError("delimiter must be non-empty")
    rng = random.Random(seed)
    header = [
        "order_id",
        "customer_name",
        "email",
        "amount_vnd",
        "qty",
        "is_paid",
        "created_date",
        "signed_at",
        "note",
    ]
    lines: list[str] = [delimiter.join(header)]
    base = date(2026, 5, 1)
    for i in range(n_rows):
        order_id = i + 1
        name = rng.choice(_VN_FIRST_NAMES)
        email = f"user{i:04d}@example.vn"
        amount_int = rng.randint(50_000, 5_000_000)
        amount_cents = rng.randint(0, 99)
        amount_str = f"{_vn_thousands(amount_int)},{amount_cents:02d}"
        qty = rng.randint(1, 10)
        is_paid = rng.choice(("Có", "Không"))
        d = base + timedelta(days=rng.randint(0, 60))
        created_date = d.strftime("%d/%m/%Y")
        signed_at = (
            datetime.combine(d, datetime.min.time())
            .replace(
                hour=rng.randint(8, 18),
                minute=rng.randint(0, 59),
                second=rng.randint(0, 59),
            )
            .isoformat()
        )
        note = "" if rng.random() < null_fraction else f"freight #{rng.randint(1, 999)}"
        row = [
            str(order_id),
            name,
            email,
            amount_str,
            str(qty),
            is_paid,
            created_date,
            signed_at,
            note,
        ]
        # Sprinkle nulls into other columns too.
        for col_idx in (1, 8):
            if col_idx != 8 and rng.random() < null_fraction:
                row[col_idx] = ""
        lines.append(delimiter.join(_csv_escape(v, delimiter) for v in row))
    return "\n".join(lines) + "\n"


def _vn_thousands(n: int) -> str:
    """Render ``n`` with periods as thousands separators (VN style)."""
    if n < 0:
        return "-" + _vn_thousands(-n)
    s = str(n)
    out_parts: list[str] = []
    while len(s) > 3:
        out_parts.append(s[-3:])
        s = s[:-3]
    out_parts.append(s)
    return ".".join(reversed(out_parts))


def _csv_escape(value: str, delimiter: str) -> str:
    """Wrap in quotes if ``value`` contains the delimiter, quote, or newline."""
    if delimiter in value or '"' in value or "\n" in value:
        escaped = value.replace('"', '""')
        return f'"{escaped}"'
    return value


__all__ = ["generate"]
