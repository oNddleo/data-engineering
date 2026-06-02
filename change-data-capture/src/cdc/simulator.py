"""Synthetic CDC stream generator.

Models a small ``orders`` + ``customers`` workload: customers are
inserted, orders are inserted and updated through a small state
machine (``pending → paid → shipped``), and a small fraction are
deleted to exercise tombstones.

Useful for replay / compaction / lineage benchmarks.
"""

from __future__ import annotations

import random

from cdc.schema import CDCEvent, EventPosition, Op, RowState


def generate(
    *,
    n_customers: int = 30,
    n_orders: int = 100,
    delete_fraction: float = 0.05,
    seed: int = 0,
    base_ts_ms: int = 1_715_251_200_000,  # 2024-05-09T00:00:00Z
    log_file: str = "binlog.000001",
) -> list[CDCEvent]:
    """Generate a synthetic event stream for ``customers`` + ``orders``."""
    if n_customers < 0 or n_orders < 0:
        raise ValueError("n_customers / n_orders must be >= 0")
    if not 0 <= delete_fraction <= 1:
        raise ValueError(f"delete_fraction must be in [0, 1], got {delete_fraction}")

    rng = random.Random(seed)
    events: list[CDCEvent] = []
    offset = 0
    ts_ms = base_ts_ms

    def _next_position() -> EventPosition:
        nonlocal offset
        offset += 1
        return EventPosition(log_file=log_file, offset=offset)

    def _next_ts() -> int:
        nonlocal ts_ms
        ts_ms += rng.randint(100, 5_000)
        return ts_ms

    # Phase 1: customer INSERTs.
    customer_pks: list[str] = []
    for i in range(n_customers):
        pk = f"C-{i:05d}"
        customer_pks.append(pk)
        events.append(
            CDCEvent(
                op=Op.CREATE,
                table="customers",
                pk=pk,
                ts_ms=_next_ts(),
                position=_next_position(),
                after={
                    "id": pk,
                    "name": f"Customer {i}",
                    "tier": rng.choice(["bronze", "silver", "gold"]),
                },
            )
        )

    if n_customers == 0:
        return events

    # Phase 2: order lifecycle for each of n_orders.
    for j in range(n_orders):
        order_pk = f"O-{j:06d}"
        cust = rng.choice(customer_pks)
        # INSERT (pending).
        initial: RowState = {
            "id": order_pk,
            "customer_id": cust,
            "status": "pending",
            "total_vnd": rng.randint(50_000, 5_000_000),
        }
        events.append(
            CDCEvent(
                op=Op.CREATE,
                table="orders",
                pk=order_pk,
                ts_ms=_next_ts(),
                position=_next_position(),
                after=initial,
            )
        )
        # UPDATE 1: pending → paid.
        paid_state: RowState = dict(initial)
        paid_state["status"] = "paid"
        events.append(
            CDCEvent(
                op=Op.UPDATE,
                table="orders",
                pk=order_pk,
                ts_ms=_next_ts(),
                position=_next_position(),
                before=initial,
                after=paid_state,
            )
        )
        # 80% of orders go on to shipped.
        current_state: RowState
        if rng.random() < 0.8:
            shipped_state: RowState = dict(paid_state)
            shipped_state["status"] = "shipped"
            events.append(
                CDCEvent(
                    op=Op.UPDATE,
                    table="orders",
                    pk=order_pk,
                    ts_ms=_next_ts(),
                    position=_next_position(),
                    before=paid_state,
                    after=shipped_state,
                )
            )
            current_state = shipped_state
        else:
            current_state = paid_state
        # delete_fraction of orders get DELETEd at the end.
        if rng.random() < delete_fraction:
            events.append(
                CDCEvent(
                    op=Op.DELETE,
                    table="orders",
                    pk=order_pk,
                    ts_ms=_next_ts(),
                    position=_next_position(),
                    before=current_state,
                )
            )

    return events


__all__ = ["generate"]
