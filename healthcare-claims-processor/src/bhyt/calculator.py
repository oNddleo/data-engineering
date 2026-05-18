"""Claim reimbursement calculator.

Steps:

1. Verify the claim's line-item math (``line_total = qty × unit_price``)
   and that the header subtotal sums to the items. Any mismatch
   flags the claim with a note but doesn't reject — VSS's back-end
   handles those at submission time; we just record the discrepancy.
2. Look up the patient's coverage rate from the card prefix.
3. Apply the referral penalty (cross-province, no-referral, tier
   bypass — except emergencies).
4. Compute ``insurer_pays = subtotal × base_bps × penalty_bps / 10_000²``
   using integer math (banker's rounding to nearest VND).
5. ``patient_pays = subtotal - insurer_pays`` (co-pay).

The function returns a :class:`Reimbursement` with the rates,
amounts, and any notes about anomalies surfaced during processing.
"""

from __future__ import annotations

from bhyt.card import decode_prefix, is_valid_format
from bhyt.coverage import effective_rate_bps
from bhyt.schema import Claim, Reimbursement


def _verify_line_math(claim: Claim) -> list[str]:
    """Returns a list of notes for math discrepancies (empty if all clean)."""
    notes: list[str] = []
    for item in claim.items:
        expected = item.quantity * item.unit_price_vnd
        if item.line_total_vnd != expected:
            notes.append(
                f"line {item.item_code}: line_total {item.line_total_vnd:,} "
                f"!= qty × unit_price {expected:,}"
            )
    expected_subtotal = sum(it.line_total_vnd for it in claim.items)
    if claim.subtotal_vnd != expected_subtotal:
        notes.append(
            f"header subtotal {claim.subtotal_vnd:,} " f"!= sum(items) {expected_subtotal:,}"
        )
    return notes


def _round_half_even(numer: int, denom: int) -> int:
    """Banker's rounding on integer division."""
    quot, rem = divmod(numer, denom)
    if rem * 2 > denom or (rem * 2 == denom and quot % 2 == 1):
        quot += 1
    return quot


def calculate(claim: Claim, *, emergency: bool = False) -> Reimbursement:
    """Compute the reimbursement for one claim.

    ``emergency=True`` waives the referral penalty per Article 22 §3.
    """
    notes: list[str] = []

    if not is_valid_format(claim.card_number):
        notes.append(f"card_number {claim.card_number!r} fails format check")
        # Without a decodable prefix we can't determine the rate;
        # return a zero-coverage record.
        return Reimbursement(
            claim_id=claim.claim_id,
            subtotal_vnd=claim.subtotal_vnd,
            coverage_rate_bps=0,
            referral_penalty_bps=0,
            insurer_pays_vnd=0,
            patient_pays_vnd=claim.subtotal_vnd,
            notes=tuple(notes),
        )

    prefix = decode_prefix(claim.card_number)
    base_bps, penalty_bps = effective_rate_bps(
        category=prefix.category,
        visited_level=claim.care_level,
        has_referral=claim.has_referral,
        same_province=claim.same_province,
        emergency=emergency,
    )

    notes.extend(_verify_line_math(claim))

    # insurer_pays = subtotal × base_bps × penalty_bps / 10_000²
    numer = claim.subtotal_vnd * base_bps * penalty_bps
    insurer_pays = _round_half_even(numer, 10_000 * 10_000)
    patient_pays = claim.subtotal_vnd - insurer_pays

    return Reimbursement(
        claim_id=claim.claim_id,
        subtotal_vnd=claim.subtotal_vnd,
        coverage_rate_bps=base_bps,
        referral_penalty_bps=penalty_bps,
        insurer_pays_vnd=insurer_pays,
        patient_pays_vnd=patient_pays,
        notes=tuple(notes),
    )


__all__ = ["calculate"]
