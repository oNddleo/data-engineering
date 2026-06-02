from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from savings_engine.storage.database import get_db
from savings_engine.storage.repository import RateRepository

router = APIRouter()


class RateOut(BaseModel):
    bank_code: str
    term_days: int
    term_label: str
    rate_pa: float
    rate_type: str
    min_amount_vnd: int | None
    currency: str

    model_config = {"from_attributes": True}


class BestRateOut(RateOut):
    rank: int


@router.get("", response_model=list[RateOut])
def get_latest_rates(
    bank_code: str | None = Query(None, description="Filter by bank code, e.g. VCB"),
    rate_type: str | None = Query(None, description="standard | online | promotional"),
    term_days: int | None = Query(None, description="Filter by canonical term in days"),
    db: Session = Depends(get_db),
) -> Any:
    """Latest rates for all banks (or a specific bank), from the most recent successful scrape."""
    repo = RateRepository(db)
    records = repo.get_latest_rates(bank_code=bank_code.upper() if bank_code else None)

    if rate_type:
        records = [r for r in records if r.rate_type == rate_type]
    if term_days is not None:
        records = [r for r in records if r.term_days == term_days]

    return [RateOut.model_validate(r) for r in records]


@router.get("/best", response_model=list[BestRateOut])
def best_rates(
    term_days: int = Query(..., description="Canonical term in days, e.g. 180"),
    rate_type: str = Query("standard", description="standard | online | promotional"),
    top_n: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> Any:
    """Top-N highest rates across all banks for a given term."""
    repo = RateRepository(db)
    records = [r for r in repo.get_best_rates(term_days, top_n=50) if r.rate_type == rate_type]
    records.sort(key=lambda r: float(r.rate_pa), reverse=True)
    records = records[:top_n]

    return [
        BestRateOut(
            bank_code=str(r.bank_code),
            term_days=int(r.term_days),
            term_label=str(r.term_label),
            rate_pa=float(r.rate_pa),
            rate_type=str(r.rate_type),
            min_amount_vnd=int(r.min_amount_vnd) if r.min_amount_vnd is not None else None,
            currency=str(r.currency),
            rank=i + 1,
        )
        for i, r in enumerate(records)
    ]


@router.get("/terms", response_model=list[int])
def available_terms(db: Session = Depends(get_db)) -> Any:
    """List all canonical term_days values that exist in the database."""
    return RateRepository(db).get_available_terms()


@router.get("/{bank_code}", response_model=list[RateOut])
def get_bank_rates(
    bank_code: str,
    rate_type: str | None = Query(None),
    db: Session = Depends(get_db),
) -> Any:
    """All latest rates for a specific bank."""
    repo = RateRepository(db)
    if not repo.get_bank(bank_code.upper()):
        raise HTTPException(404, f"Bank '{bank_code}' not found")
    records = repo.get_latest_rates(bank_code=bank_code.upper())
    if rate_type:
        records = [r for r in records if r.rate_type == rate_type]
    return [RateOut.model_validate(r) for r in records]
