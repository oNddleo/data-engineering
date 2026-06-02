"""Seeded synthetic invoice generator.

Produces invoices spanning the four legal VAT rates and the three
invoice kinds. With ``bad_fraction > 0`` a configurable share of
invoices have deliberately injected errors so the validator has
something to flag.

Injected errors (one per bad invoice, picked at random):

* Line-total math off by ±1 VND.
* VAT amount off by a small constant.
* Header total mismatched with sum of lines.
* Wrong template/kind pairing.
* Invalid buyer MST (corrupted check digit).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from vntax.schema import VN_TZ, Invoice, InvoiceItem, InvoiceKind, TaxCode, VATRate

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


# Valid MSTs from the bundled registry. Mixing real + computed-valid
# entries is fine for synthetic data.
_VALID_SELLERS: tuple[tuple[str, str], ...] = (
    ("0100109106", "Vietcombank"),
    ("0301442379", "Công ty CP FPT"),
    ("0301448243", "Mobile World Investment Corp"),
    ("0309532909", "Vietjet Aviation"),
)

_VALID_BUYERS: tuple[tuple[str, str], ...] = (
    ("0100686978", "Vingroup (mock)"),
    ("0312901271", "Tiki Corp (mock)"),
)


_TEMPLATE_BY_KIND: dict[InvoiceKind, str] = {
    InvoiceKind.VAT_INVOICE: "1/001",
    InvoiceKind.SALES_INVOICE: "2/001",
    InvoiceKind.EXPORT_INVOICE: "6/001",
}


def _round_vat(line_total: int, rate: VATRate) -> int:
    if rate is VATRate.EXEMPT:
        return 0
    rate_bps: int = rate.value
    numer = line_total * rate_bps
    denom = 10_000
    quot, rem = divmod(numer, denom)
    quot_int: int = quot
    if rem * 2 > denom or (rem * 2 == denom and quot_int % 2 == 1):
        quot_int += 1
    return quot_int


def _make_invoice(
    rng: random.Random,
    idx: int,
    base: datetime,
    kind: InvoiceKind,
    bad: bool,
) -> Invoice:
    seller_mst, seller_name = rng.choice(_VALID_SELLERS)
    if kind is InvoiceKind.EXPORT_INVOICE:
        buyer_mst = None
        buyer_name = "Foreign Buyer Ltd"
    else:
        buyer_mst_raw, buyer_name = rng.choice(_VALID_BUYERS)
        buyer_mst = TaxCode(digits=buyer_mst_raw)

    vat_choices: tuple[VATRate, ...] = (
        (VATRate.ZERO,)
        if kind is InvoiceKind.EXPORT_INVOICE
        else (VATRate.FIVE, VATRate.EIGHT, VATRate.TEN, VATRate.EXEMPT)
    )

    n_lines = rng.randint(1, 4)
    items: list[InvoiceItem] = []
    for line_no in range(1, n_lines + 1):
        qty = rng.randint(1, 10)
        unit_price = rng.choice((49_000, 99_000, 199_000, 499_000, 990_000, 1_990_000))
        line_total = qty * unit_price
        rate = rng.choice(vat_choices)
        vat_amt = _round_vat(line_total, rate)
        items.append(
            InvoiceItem(
                line_no=line_no,
                description=f"Hàng hoá / dịch vụ dòng {line_no}",
                quantity=qty,
                unit_price_vnd=unit_price,
                vat_rate=rate,
                line_total_vnd=line_total,
                vat_amount_vnd=vat_amt,
            )
        )

    subtotal = sum(i.line_total_vnd for i in items)
    vat_total = sum(i.vat_amount_vnd for i in items)
    grand = subtotal + vat_total
    template = _TEMPLATE_BY_KIND[kind]

    if bad:
        bug = rng.choice(("line_off", "vat_off", "header_off", "wrong_template", "bad_buyer_mst"))
        if bug == "line_off" and items:
            # Inflate the first line's line_total by 1 VND.
            bad_item = items[0]
            items[0] = InvoiceItem(
                line_no=bad_item.line_no,
                description=bad_item.description,
                quantity=bad_item.quantity,
                unit_price_vnd=bad_item.unit_price_vnd,
                vat_rate=bad_item.vat_rate,
                line_total_vnd=bad_item.line_total_vnd + 1,
                vat_amount_vnd=bad_item.vat_amount_vnd,
            )
            subtotal = sum(i.line_total_vnd for i in items)
            grand = subtotal + vat_total
        elif bug == "vat_off" and items:
            bad_item = items[0]
            items[0] = InvoiceItem(
                line_no=bad_item.line_no,
                description=bad_item.description,
                quantity=bad_item.quantity,
                unit_price_vnd=bad_item.unit_price_vnd,
                vat_rate=bad_item.vat_rate,
                line_total_vnd=bad_item.line_total_vnd,
                vat_amount_vnd=bad_item.vat_amount_vnd + 100,
            )
            vat_total = sum(i.vat_amount_vnd for i in items)
            grand = subtotal + vat_total
        elif bug == "header_off":
            grand = grand + 1_000  # header doesn't match sum
        elif bug == "wrong_template" and kind is not InvoiceKind.EXPORT_INVOICE:
            template = _TEMPLATE_BY_KIND[InvoiceKind.EXPORT_INVOICE]
        elif bug == "bad_buyer_mst" and buyer_mst is not None:
            # Mutate the last digit to break the checksum.
            mutated = buyer_mst.digits[:-1] + str((int(buyer_mst.digits[-1]) + 1) % 10)
            buyer_mst = TaxCode(digits=mutated)

    return Invoice(
        invoice_id=f"INV-{idx:08d}",
        serial=f"K{rng.randint(20, 29)}TAA",
        template_code=template,
        invoice_number=idx + 1,
        kind=kind,
        seller_tax_code=TaxCode(digits=seller_mst),
        seller_name=seller_name,
        buyer_tax_code=buyer_mst,
        buyer_name=buyer_name,
        issued_at=base + timedelta(minutes=idx * 7),
        items=tuple(items),
        subtotal_vnd=subtotal,
        vat_total_vnd=vat_total,
        grand_total_vnd=grand,
    )


def generate(
    *,
    n_invoices: int = 100,
    bad_fraction: float = 0.20,
    seed: int = 0,
    base_time: datetime | None = None,
) -> list[Invoice]:
    """Generate a mixed batch of valid + intentionally bad invoices."""
    if n_invoices < 1:
        raise ValueError("n_invoices must be >= 1")
    if not 0.0 <= bad_fraction <= 1.0:
        raise ValueError("bad_fraction must be in [0, 1]")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS
    out: list[Invoice] = []
    for idx in range(n_invoices):
        kind = rng.choices(
            (InvoiceKind.VAT_INVOICE, InvoiceKind.SALES_INVOICE, InvoiceKind.EXPORT_INVOICE),
            weights=(0.70, 0.20, 0.10),
            k=1,
        )[0]
        bad = rng.random() < bad_fraction
        out.append(_make_invoice(rng, idx, base, kind, bad))
    return out


__all__ = ["generate"]
