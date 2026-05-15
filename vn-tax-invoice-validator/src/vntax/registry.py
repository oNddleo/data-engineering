"""Tax-registry lookup Protocol + bundled in-memory mock.

Production callers plug in their GDT API client behind the
:class:`TaxRegistry` Protocol. The bundled :class:`InMemoryRegistry`
is what tests and the demo CLI use — it's seeded with a handful of
real public Vietnamese tax codes (Vietcombank, FPT, etc.) so the
``vntax lookup`` command does something useful out of the box.

The Protocol is intentionally minimal: just ``lookup(mst) →
TaxEntity | None``. Everything else (cache TTLs, retries, fallback
to a stale snapshot) is a production concern that doesn't belong in
the contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TaxEntity:
    """One row from the GDT tax-payer registry (Đăng ký thuế)."""

    mst: str  # canonical 10- or 13-digit form
    name: str  # legal name
    address: str
    status: str  # "ACTIVE", "SUSPENDED", "CLOSED"
    registered_at: str  # ISO date


class TaxRegistry(Protocol):
    """Anything that can answer "is this MST live?" implements this."""

    def lookup(self, mst: str) -> TaxEntity | None: ...


class InMemoryRegistry:
    """Dict-backed registry — bundled for tests / demos."""

    def __init__(self, entities: list[TaxEntity] | None = None) -> None:
        self._by_mst: dict[str, TaxEntity] = {}
        # ``entities=[]`` must mean "no seed" — using ``is None`` (not a
        # truthy check) so an explicit empty list doesn't silently get
        # the bundled defaults.
        seed = _bundled_entities() if entities is None else entities
        for e in seed:
            self._by_mst[e.mst] = e

    def lookup(self, mst: str) -> TaxEntity | None:
        # 13-digit codes resolve to their 10-digit parent if the branch
        # isn't separately registered — that matches how the real GDT
        # registry handles unregistered branch suffixes.
        hit = self._by_mst.get(mst)
        if hit is not None:
            return hit
        if len(mst) == 13:
            return self._by_mst.get(mst[:10])
        return None

    def add(self, entity: TaxEntity) -> None:
        """Insert / replace a registry entry (for tests)."""
        self._by_mst[entity.mst] = entity


def _bundled_entities() -> list[TaxEntity]:
    """Seven seed MSTs — checksum-valid; names match real public VN
    entities where the published MST and the algorithm agree, mock
    otherwise. Every entry passes ``taxcode.is_valid``."""
    return [
        TaxEntity(
            mst="0100109106",
            name="Vietcombank",
            address="198 Trần Quang Khải, Hoàn Kiếm, Hà Nội",
            status="ACTIVE",
            registered_at="1993-04-01",
        ),
        TaxEntity(
            mst="0301442379",
            name="Công ty CP FPT",
            address="17 Duy Tân, Cầu Giấy, Hà Nội",
            status="ACTIVE",
            registered_at="2002-03-13",
        ),
        TaxEntity(
            mst="0100686978",
            name="Vingroup (mock)",
            address="7 Bằng Lăng 1, Vinhomes Riverside, Long Biên, Hà Nội",
            status="ACTIVE",
            registered_at="2002-08-08",
        ),
        TaxEntity(
            mst="0301448243",
            name="Mobile World Investment Corp",
            address="128 Trần Quang Khải, Tân Định, Q.1, TP HCM",
            status="ACTIVE",
            registered_at="2004-03-16",
        ),
        TaxEntity(
            mst="0312901271",
            name="Tiki Corp (mock)",
            address="52 Út Tịch, P.4, Tân Bình, TP HCM",
            status="ACTIVE",
            registered_at="2014-09-19",
        ),
        TaxEntity(
            mst="0309532909",
            name="Vietjet Aviation",
            address="302/3 Kim Mã, Ngọc Khánh, Ba Đình, Hà Nội",
            status="ACTIVE",
            registered_at="2007-11-13",
        ),
        TaxEntity(
            mst="0102156359",
            name="Mock Defunct Co",
            address="(suspended)",
            status="SUSPENDED",
            registered_at="2006-04-01",
        ),
    ]


__all__ = ["InMemoryRegistry", "TaxEntity", "TaxRegistry"]
