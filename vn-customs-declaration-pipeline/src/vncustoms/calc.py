"""Customs value + duty + VAT calculator.

Algorithm (for an import declaration):

1. **Customs value** (``trị giá tính thuế``) — landed cost at the
   VN port-of-import. Built up to CIF equivalent:

   * EXW: line_total + freight + insurance
   * FOB: line_total + freight + insurance (insurance + freight already
     paid separately by buyer)
   * CFR: line_total + insurance (freight bundled into invoice)
   * CIF: line_total (everything bundled)
   * DAP/DDP: line_total (seller pays through to delivery)

   Freight & insurance are pro-rated across lines by their share of the
   total invoice value.

2. **Import duty** = customs_value × duty_rate(HS chapter).
3. **VAT base** = customs_value + import_duty.
4. **VAT** = vat_base × vat_rate(HS chapter).
5. **Total tax** = import_duty + VAT, converted to VND at
   ``declaration.usd_to_vnd``.

All money in this calculator stays in **USD cents** until the very last
conversion step, where we go to integer **VND** with banker's rounding.
"""

from __future__ import annotations

from dataclasses import dataclass

from vncustoms.schema import Declaration, DeclarationKind, Incoterm
from vncustoms.tariff import duty_rate_for, vat_rate_for


@dataclass(frozen=True, slots=True)
class LineCalc:
    """Per-line tax result."""

    description: str
    hs_code: str
    quantity: int
    customs_value_usd_cents: int
    import_duty_usd_cents: int
    vat_usd_cents: int

    @property
    def total_tax_usd_cents(self) -> int:
        return self.import_duty_usd_cents + self.vat_usd_cents


@dataclass(frozen=True, slots=True)
class DeclarationCalc:
    """Full declaration tax result."""

    declaration_no: str
    lines: tuple[LineCalc, ...]
    customs_value_usd_cents: int
    import_duty_usd_cents: int
    vat_usd_cents: int
    total_tax_vnd: int

    @property
    def total_tax_usd_cents(self) -> int:
        return self.import_duty_usd_cents + self.vat_usd_cents


def _includes_freight(incoterm: Incoterm) -> bool:
    return incoterm in (Incoterm.CFR, Incoterm.CIF, Incoterm.DAP, Incoterm.DDP)


def _includes_insurance(incoterm: Incoterm) -> bool:
    return incoterm in (Incoterm.CIF, Incoterm.DAP, Incoterm.DDP)


def compute(decl: Declaration) -> DeclarationCalc:
    """Compute customs value + duties + VAT for an import declaration.

    Exports are tax-free in this lightweight calculator (return zero
    duty + zero VAT — VN export duty applies to a short list of natural
    resources we don't model here).
    """
    if decl.kind == DeclarationKind.EXPORT:
        return _zero_calc(decl)

    lines_total = sum(line.total_usd_cents for line in decl.lines)
    if lines_total == 0:
        return _zero_calc(decl)

    # Determine freight/insurance to add (uncovered by incoterm).
    add_freight = 0 if _includes_freight(decl.incoterm) else decl.freight_usd_cents
    add_insurance = 0 if _includes_insurance(decl.incoterm) else decl.insurance_usd_cents
    addons = add_freight + add_insurance

    # Allocate addons across lines proportional to line value.
    line_calcs: list[LineCalc] = []
    cv_sum = 0
    duty_sum = 0
    vat_sum = 0
    for i, line in enumerate(decl.lines):
        share = line.total_usd_cents / lines_total
        # Last line absorbs rounding remainder to keep sums exact.
        if i == len(decl.lines) - 1:
            line_addon = addons - sum(
                round(other.total_usd_cents / lines_total * addons) for other in decl.lines[:-1]
            )
        else:
            line_addon = round(line.total_usd_cents / lines_total * addons)
        _ = share  # share kept for clarity; line_addon already uses it

        cv = line.total_usd_cents + line_addon
        duty_rate = duty_rate_for(line.hs_code.chapter)
        duty = round(cv * duty_rate)
        vat_rate = vat_rate_for(line.hs_code.chapter)
        vat = round((cv + duty) * vat_rate)

        line_calcs.append(
            LineCalc(
                description=line.description,
                hs_code=line.hs_code.code,
                quantity=line.quantity,
                customs_value_usd_cents=cv,
                import_duty_usd_cents=duty,
                vat_usd_cents=vat,
            )
        )
        cv_sum += cv
        duty_sum += duty
        vat_sum += vat

    total_tax_usd_cents = duty_sum + vat_sum
    # Convert USD cents → VND. usd_to_vnd is VND per 1 USD, so
    # total_vnd = total_usd_cents / 100 * usd_to_vnd. We use integer
    # math to avoid float drift.
    total_tax_vnd = (total_tax_usd_cents * decl.usd_to_vnd) // 100

    return DeclarationCalc(
        declaration_no=decl.declaration_no,
        lines=tuple(line_calcs),
        customs_value_usd_cents=cv_sum,
        import_duty_usd_cents=duty_sum,
        vat_usd_cents=vat_sum,
        total_tax_vnd=total_tax_vnd,
    )


def _zero_calc(decl: Declaration) -> DeclarationCalc:
    return DeclarationCalc(
        declaration_no=decl.declaration_no,
        lines=tuple(
            LineCalc(
                description=line.description,
                hs_code=line.hs_code.code,
                quantity=line.quantity,
                customs_value_usd_cents=line.total_usd_cents,
                import_duty_usd_cents=0,
                vat_usd_cents=0,
            )
            for line in decl.lines
        ),
        customs_value_usd_cents=sum(line.total_usd_cents for line in decl.lines),
        import_duty_usd_cents=0,
        vat_usd_cents=0,
        total_tax_vnd=0,
    )


__all__ = ["DeclarationCalc", "LineCalc", "compute"]
