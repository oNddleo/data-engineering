"""Seeded synthetic transaction generator covering every fraud signal."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fraudvn.schema import VN_TZ, Channel, TransactionRequest

if TYPE_CHECKING:
    from collections.abc import Iterable


_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


_BENIGN_NARRATIVES = (
    "tien an trua",
    "tra tien dien",
    "Goi me tien sinh hoat",
    "Thanh toan tien hoc cho con",
    "Chuyen khoan luong tu Vingroup",
    "",
)

_SCAM_TEXTS: dict[str, str] = {
    "cong_an": "Chuyển khoản theo yêu cầu Công An phục vụ điều tra vụ án",
    "chuyen_nham": "Em chuyển nhầm, anh chuyển lại giúp em với",
    "crypto": "Đầu tư crypto sàn ABC lợi nhuận cao mỗi ngày",
    "job_scam": "Tuyển CTV online việc nhẹ lương cao",
    "loan_scam": "Vay tiền online không thế chấp app vay",
}


def _account(rng: random.Random) -> str:
    return "ACC-" + "".join(str(rng.randint(0, 9)) for _ in range(8))


def _benign_amount(rng: random.Random) -> int:
    return rng.randint(50_000, 4_000_000)


def _channel(rng: random.Random) -> Channel:
    return rng.choices(list(Channel), weights=[0.7, 0.2, 0.07, 0.03], k=1)[0]


def _next_id(state: dict[str, int], prefix: str) -> str:
    state[prefix] = state.get(prefix, 0) + 1
    return f"{prefix}-{state[prefix]:06d}"


def _make_req(
    rng: random.Random,
    *,
    txn_id: str,
    src: str,
    dst: str,
    amount: int,
    narrative: str,
    occurred_at: datetime,
    bank_bin: str = "970418",
    otp_delta_seconds: float | None = None,
) -> TransactionRequest:
    otp_issued = None
    otp_verified = None
    if otp_delta_seconds is not None:
        otp_issued = occurred_at - timedelta(seconds=30)
        otp_verified = otp_issued + timedelta(seconds=otp_delta_seconds)
    return TransactionRequest(
        txn_id=txn_id,
        initiator_account=src,
        beneficiary_account=dst,
        beneficiary_bank_bin=bank_bin,
        amount_vnd=amount,
        narrative=narrative,
        channel=_channel(rng),
        occurred_at=occurred_at,
        otp_issued_at=otp_issued,
        otp_verified_at=otp_verified,
    )


def generate(
    *,
    n_benign: int = 50,
    inject_scams: Iterable[str] = (),
    inject_blacklist: int = 0,
    inject_velocity: int = 0,
    inject_otp_race: int = 0,
    inject_round_below: int = 0,
    blacklist: Iterable[str] = (),
    seed: int = 0,
    base_time: datetime | None = None,
) -> list[TransactionRequest]:
    """Produce a deterministic stream of transaction requests.

    Each non-zero ``inject_*`` parameter adds a fully-formed scam
    pattern that the engine should flag. ``inject_scams`` accepts
    any subset of ``("cong_an", "chuyen_nham", "crypto", "job_scam",
    "loan_scam")`` — each gets one transaction with the matching
    Vietnamese narrative.
    """
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS
    bl = list(blacklist)
    state: dict[str, int] = {}
    out: list[TransactionRequest] = []

    # Benign baseline.
    for i in range(n_benign):
        out.append(
            _make_req(
                rng,
                txn_id=_next_id(state, "BEN"),
                src=_account(rng),
                dst=_account(rng),
                amount=_benign_amount(rng),
                narrative=rng.choice(_BENIGN_NARRATIVES),
                occurred_at=base + timedelta(seconds=i * 60),
            )
        )

    # Keyword scams — one per requested kind.
    for kind in inject_scams:
        if kind not in _SCAM_TEXTS:
            raise ValueError(f"unknown scam kind: {kind!r}")
        out.append(
            _make_req(
                rng,
                txn_id=_next_id(state, "SCAM"),
                src=_account(rng),
                dst=_account(rng),
                amount=rng.randint(8_000_000, 50_000_000),
                narrative=_SCAM_TEXTS[kind],
                occurred_at=base + timedelta(hours=2),
            )
        )

    # Blacklist beneficiary.
    for k in range(inject_blacklist):
        if not bl:
            break
        out.append(
            _make_req(
                rng,
                txn_id=_next_id(state, "BL"),
                src=_account(rng),
                dst=bl[k % len(bl)],
                amount=rng.randint(1_000_000, 5_000_000),
                narrative=rng.choice(_BENIGN_NARRATIVES),
                occurred_at=base + timedelta(hours=3, seconds=k * 30),
            )
        )

    # Velocity burst — 6 outgoing in 1 minute from one account.
    for k in range(inject_velocity):
        src = _account(rng)
        anchor = base + timedelta(hours=4 + k)
        for j in range(6):
            out.append(
                _make_req(
                    rng,
                    txn_id=_next_id(state, "VEL"),
                    src=src,
                    dst=_account(rng),
                    amount=rng.randint(500_000, 2_000_000),
                    narrative=rng.choice(_BENIGN_NARRATIVES),
                    occurred_at=anchor + timedelta(seconds=j * 10),
                )
            )

    # OTP race — verified 2s after issuance.
    for k in range(inject_otp_race):
        out.append(
            _make_req(
                rng,
                txn_id=_next_id(state, "OTP"),
                src=_account(rng),
                dst=_account(rng),
                amount=rng.randint(1_000_000, 5_000_000),
                narrative=rng.choice(_BENIGN_NARRATIVES),
                occurred_at=base + timedelta(hours=5, seconds=k * 30),
                otp_delta_seconds=2.0,
            )
        )

    # Round amount just below 10M.
    for k in range(inject_round_below):
        out.append(
            _make_req(
                rng,
                txn_id=_next_id(state, "RND"),
                src=_account(rng),
                dst=_account(rng),
                amount=rng.randint(9_600_000, 9_999_000),
                narrative=rng.choice(_BENIGN_NARRATIVES),
                occurred_at=base + timedelta(hours=6, seconds=k * 30),
            )
        )

    out.sort(key=lambda r: r.occurred_at)
    return out


__all__ = ["generate"]
