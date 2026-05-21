"""JSONL I/O tests for VN telecom billing pipeline."""

from __future__ import annotations

import json

from vntelecom.billing import bill
from vntelecom.io_jsonl import dump_billed, dump_cdrs, load_and_bill
from vntelecom.schema import CDR, CallType, Operator, ServiceType


def _sample_cdr(cdr_id: str = "CDR-001") -> CDR:
    return CDR(
        cdr_id=cdr_id,
        subscriber_msisdn="0901234567",
        operator=Operator.VIETTEL,
        service_type=ServiceType.VOICE,
        call_type=CallType.ON_NET,
        duration_seconds=120,
        timestamp_epoch_s=1_748_700_000,
        destination_msisdn="0987654321",
        is_prepaid=True,
    )


def test_dump_cdrs_is_jsonl() -> None:
    cdrs = [_sample_cdr("A"), _sample_cdr("B")]
    text = dump_cdrs(cdrs)
    lines = [ln for ln in text.strip().splitlines() if ln]
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "cdr_id" in obj
        assert "service_type" in obj


def test_dump_billed_is_jsonl() -> None:
    billed = [bill(_sample_cdr())]
    text = dump_billed(billed)
    obj = json.loads(text.strip())
    assert obj["billing_unit"] == "min"
    assert obj["base_charge_vnd"] > 0


def test_load_and_bill_roundtrip() -> None:
    cdr = _sample_cdr()
    text = dump_cdrs([cdr])
    billed = load_and_bill(text)
    assert len(billed) == 1
    assert billed[0].cdr_id == "CDR-001"
    assert billed[0].total_charge_vnd > 0


def test_empty_text_returns_empty() -> None:
    assert load_and_bill("") == []


def test_dump_billed_empty() -> None:
    assert dump_billed([]) == ""
