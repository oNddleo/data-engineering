"""Seeded synthetic VN-customer rowset with intentional defects.

Generates a ``customer`` table whose columns exercise every bundled
check:

* ``customer_id`` (uniqueness)
* ``cccd`` (12-digit format)
* ``mst`` (10/13-digit + checksum)
* ``phone`` (VN format)
* ``bank_account`` (8-19 digits)
* ``postal_code`` (5-digit + province prefix)
* ``tier`` (in_set: BASIC / STANDARD / PREFERRED / MALL)
* ``credit_limit_vnd`` (range_int)

``defect_fraction`` of rows have one defect injected at random.
"""

from __future__ import annotations

import random

from dqkit.checks_vn import _MST_WEIGHTS

_VALID_PROVINCE_CODES_LIST = [
    "001",
    "002",
    "004",
    "008",
    "010",
    "024",
    "036",
    "077",
    "079",
    "087",
    "095",
]
_TIERS = ("BASIC", "STANDARD", "PREFERRED", "MALL")


def _compute_mst_check(digits9: str) -> int:
    total = sum(int(d) * w for d, w in zip(digits9, _MST_WEIGHTS, strict=True))
    mod = total % 11
    return 0 if mod == 0 else 10 - mod


def _make_valid_mst(rng: random.Random, n13: bool = False) -> str:
    prefix = "".join(str(rng.randint(0, 9)) for _ in range(9))
    check = str(_compute_mst_check(prefix))
    primary = prefix + check
    if n13:
        return primary + f"{rng.randint(0, 999):03d}"
    return primary


def _make_valid_cccd(rng: random.Random) -> str:
    province = rng.choice(_VALID_PROVINCE_CODES_LIST)
    gender_century = str(rng.randint(0, 5))
    yy = f"{rng.randint(50, 99):02d}"
    seq = f"{rng.randint(1, 999_999):06d}"
    return f"{province}{gender_century}{yy}{seq}"


def _make_valid_phone(rng: random.Random) -> str:
    prefix = rng.choice(("03", "05", "07", "08", "09"))
    return prefix + "".join(str(rng.randint(0, 9)) for _ in range(8))


def _make_valid_bank_account(rng: random.Random) -> str:
    n = rng.randint(10, 16)
    return "".join(str(rng.randint(0, 9)) for _ in range(n))


def _make_valid_postal(rng: random.Random) -> str:
    prov = f"{rng.randint(10, 99):02d}"
    return prov + f"{rng.randint(0, 999):03d}"


def generate(
    *,
    n_rows: int = 100,
    defect_fraction: float = 0.20,
    seed: int = 0,
) -> list[dict[str, str | int | None]]:
    """Generate ``n_rows`` customer-table rows with intentional defects."""
    if n_rows < 1:
        raise ValueError("n_rows must be >= 1")
    if not 0.0 <= defect_fraction <= 1.0:
        raise ValueError("defect_fraction must be in [0, 1]")
    rng = random.Random(seed)
    out: list[dict[str, str | int | None]] = []
    seen_ids: set[str] = set()
    for i in range(n_rows):
        cid = f"C-{i:06d}"
        seen_ids.add(cid)
        row: dict[str, str | int | None] = {
            "customer_id": cid,
            "cccd": _make_valid_cccd(rng),
            "mst": _make_valid_mst(rng, n13=rng.random() < 0.3),
            "phone": _make_valid_phone(rng),
            "bank_account": _make_valid_bank_account(rng),
            "postal_code": _make_valid_postal(rng),
            "tier": rng.choice(_TIERS),
            "credit_limit_vnd": rng.choice((10_000_000, 30_000_000, 50_000_000)),
        }
        if rng.random() < defect_fraction:
            defect = rng.choice(
                (
                    "cccd_short",
                    "mst_mutated",
                    "phone_bad",
                    "tier_unknown",
                    "credit_out_of_range",
                    "postal_short",
                    "duplicate_id",
                    "cccd_null",
                    "mst_null",
                    "bank_too_short",
                )
            )
            if defect == "cccd_short":
                cccd_val = row["cccd"]
                assert isinstance(cccd_val, str)
                row["cccd"] = cccd_val[:11]
            elif defect == "mst_mutated":
                mst_val = row["mst"]
                assert isinstance(mst_val, str)
                bad_check = str((int(mst_val[9]) + 1) % 10)
                row["mst"] = mst_val[:9] + bad_check + mst_val[10:]
            elif defect == "phone_bad":
                row["phone"] = "01234"
            elif defect == "tier_unknown":
                row["tier"] = "PLATINUM"
            elif defect == "credit_out_of_range":
                row["credit_limit_vnd"] = -5_000_000
            elif defect == "postal_short":
                row["postal_code"] = "1234"
            elif defect == "duplicate_id" and out:
                # Reuse an earlier customer_id.
                row["customer_id"] = out[0]["customer_id"]
            elif defect == "cccd_null":
                row["cccd"] = None
            elif defect == "mst_null":
                row["mst"] = None
            elif defect == "bank_too_short":
                row["bank_account"] = "123"
        out.append(row)
    return out


__all__ = ["generate"]
