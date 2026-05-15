"""Real-time fraud-detection orchestrator.

The engine runs every signal detector against an incoming
:class:`TransactionRequest`, aggregates points into a score, maps
score to :class:`Decision`, and updates per-account state. The
whole evaluation is wrapped in ``time.perf_counter`` so the
``latency_ms`` field on the returned decision is observable —
production sets an SLO at < 200 ms.

Score tiers:

* ``score < REVIEW_THRESHOLD`` → ALLOW
* ``REVIEW_THRESHOLD ≤ score < BLOCK_THRESHOLD`` → REVIEW
* ``score ≥ BLOCK_THRESHOLD`` → BLOCK

A single CRIT signal (BLACKLIST_BENEFICIARY at 100 pts) lands you
in BLOCK on its own. Multiple weak signals stack — e.g. NIGHT (10)
+ NEW_BENEFICIARY_LARGE (25) + JOB_SCAM (30) = 65 → REVIEW.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fraudvn.schema import Decision, FraudDecision, SignalHit
from fraudvn.signals import (
    signal_beneficiary_hot,
    signal_blacklist_beneficiary,
    signal_keyword,
    signal_new_beneficiary_large,
    signal_night_transfer,
    signal_otp_race,
    signal_round_amount_below,
    signal_velocity_burst,
)
from fraudvn.state import StateStore

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fraudvn.schema import TransactionRequest


REVIEW_THRESHOLD = 50
BLOCK_THRESHOLD = 100


def score_to_decision(score: int) -> Decision:
    if score >= BLOCK_THRESHOLD:
        return Decision.BLOCK
    if score >= REVIEW_THRESHOLD:
        return Decision.REVIEW
    return Decision.ALLOW


class FraudEngine:
    """Stateful real-time fraud detector for VN internet banking."""

    def __init__(
        self,
        *,
        blacklist: Iterable[str] = (),
        review_threshold: int = REVIEW_THRESHOLD,
        block_threshold: int = BLOCK_THRESHOLD,
    ) -> None:
        if review_threshold >= block_threshold:
            raise ValueError("review_threshold must be < block_threshold")
        self._blacklist: frozenset[str] = frozenset(blacklist)
        self._review_threshold = review_threshold
        self._block_threshold = block_threshold
        self._state = StateStore()

    @property
    def state(self) -> StateStore:
        return self._state

    @property
    def blacklist_size(self) -> int:
        return len(self._blacklist)

    def evaluate(self, req: TransactionRequest) -> FraudDecision:
        """Run all signals, decide, update state, return the verdict."""
        start = time.perf_counter()
        src_state = self._state.get(req.initiator_account)
        dst_state = self._state.get(req.beneficiary_account)

        hits: list[SignalHit] = []
        hits.extend(signal_keyword(req))
        hits.extend(signal_blacklist_beneficiary(req, blacklist=self._blacklist))
        hits.extend(signal_new_beneficiary_large(req, src_state=src_state))
        hits.extend(signal_night_transfer(req))
        hits.extend(signal_otp_race(req))
        hits.extend(signal_round_amount_below(req))
        hits.extend(signal_velocity_burst(req, src_state=src_state))
        hits.extend(signal_beneficiary_hot(req, dst_state=dst_state))

        hits.sort(key=lambda h: (-h.points, h.name))
        score = sum(h.points for h in hits)

        if score >= self._block_threshold:
            decision = Decision.BLOCK
        elif score >= self._review_threshold:
            decision = Decision.REVIEW
        else:
            decision = Decision.ALLOW

        latency_ms = (time.perf_counter() - start) * 1000.0
        # Update state — even blocked transfers age the velocity counter so
        # the second / third attempt accumulates VELOCITY_BURST on its own.
        self._state.record(req)
        return FraudDecision(
            txn_id=req.txn_id,
            decision=decision,
            score=score,
            signals=tuple(hits),
            latency_ms=latency_ms,
        )

    def evaluate_many(self, reqs: Iterable[TransactionRequest]) -> list[FraudDecision]:
        return [self.evaluate(r) for r in reqs]


__all__ = ["BLOCK_THRESHOLD", "REVIEW_THRESHOLD", "FraudEngine", "score_to_decision"]
