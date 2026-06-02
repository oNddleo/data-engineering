from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from savings_engine.storage.database import get_db
from savings_engine.storage.repository import RateRepository

router = APIRouter()


class BankOut(BaseModel):
    code: str
    name_vi: str
    name_en: str
    website: str | None
    snapshot_count: int

    model_config = {"from_attributes": True}


@router.get("", response_model=list[BankOut])
def list_banks(db: Session = Depends(get_db)) -> Any:
    """Return all active banks tracked by the engine."""
    repo = RateRepository(db)
    banks = repo.get_all_banks()
    return [
        BankOut(
            code=str(b.code),
            name_vi=str(b.name_vi),
            name_en=str(b.name_en),
            website=str(b.website) if b.website is not None else None,
            snapshot_count=repo.get_snapshot_count(str(b.code)),
        )
        for b in banks
    ]


@router.get("/{bank_code}", response_model=BankOut)
def get_bank(bank_code: str, db: Session = Depends(get_db)) -> Any:
    repo = RateRepository(db)
    bank = repo.get_bank(bank_code.upper())
    if not bank:
        raise HTTPException(404, f"Bank '{bank_code}' not found")
    return BankOut(
        code=str(bank.code),
        name_vi=str(bank.name_vi),
        name_en=str(bank.name_en),
        website=str(bank.website) if bank.website is not None else None,
        snapshot_count=repo.get_snapshot_count(str(bank.code)),
    )
