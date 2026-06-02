"""Annual usage roll-up per customer.

Groups a stream of ``ElectricityBill``s by ``customer_code`` (which
implicitly groups by category and provincial unit too) and produces a
single annual summary per customer. Useful for billing audits,
year-end statements, and capacity planning.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evn.schema import CustomerCategory, ElectricityBill


@dataclass(frozen=True, slots=True)
class AnnualSummary:
    """One customer's totals over the supplied bills."""

    customer_code: str
    category: CustomerCategory
    n_bills: int
    total_kwh: int
    total_pre_vat_vnd: int
    total_vat_vnd: int

    def __post_init__(self) -> None:
        if self.n_bills < 0:
            raise ValueError(f"n_bills must be >= 0, got {self.n_bills}")
        if self.total_kwh < 0:
            raise ValueError(f"total_kwh must be >= 0, got {self.total_kwh}")
        if self.total_pre_vat_vnd < 0:
            raise ValueError("total_pre_vat_vnd must be >= 0")
        if self.total_vat_vnd < 0:
            raise ValueError("total_vat_vnd must be >= 0")

    @property
    def total_amount_vnd(self) -> int:
        return self.total_pre_vat_vnd + self.total_vat_vnd

    @property
    def average_kwh_per_bill(self) -> float:
        return self.total_kwh / self.n_bills if self.n_bills > 0 else 0.0


def aggregate_annual(bills: list[ElectricityBill]) -> list[AnnualSummary]:
    """Aggregate bills into per-customer annual summaries.

    Output sorted by ``customer_code`` ascending.
    """
    groups: dict[str, list[ElectricityBill]] = defaultdict(list)
    for b in bills:
        groups[b.customer_code].append(b)

    out: list[AnnualSummary] = []
    for customer_code, group in groups.items():
        # Category is derived from the first bill; we enforce homogeneity below.
        first_cat = group[0].category
        for b in group:
            if b.category is not first_cat:
                raise ValueError(
                    f"customer {customer_code} has mixed categories: "
                    f"{first_cat.value} and {b.category.value}",
                )
        out.append(
            AnnualSummary(
                customer_code=customer_code,
                category=first_cat,
                n_bills=len(group),
                total_kwh=sum(b.kwh_used for b in group),
                total_pre_vat_vnd=sum(b.pre_vat_amount_vnd for b in group),
                total_vat_vnd=sum(b.vat_amount_vnd for b in group),
            )
        )
    out.sort(key=lambda s: s.customer_code)
    return out


__all__ = ["AnnualSummary", "aggregate_annual"]
