"""Simulator + anomaly-injection tests."""

from __future__ import annotations

import pytest

from ekycpipe.bca import BCADatabase
from ekycpipe.ocr import MockOCREngine
from ekycpipe.pipeline import process_image
from ekycpipe.simulator import generate


def test_generate_n_citizens_count():
    ocr_map, bca = generate(n_citizens=15, seed=0)
    assert len(ocr_map) == 15
    assert len(bca) == 15


def test_generate_reproducible_with_seed():
    a_ocr, a_bca = generate(n_citizens=5, seed=42)
    b_ocr, b_bca = generate(n_citizens=5, seed=42)
    assert set(a_ocr.keys()) == set(b_ocr.keys())
    assert [r.cccd for r in a_bca] == [r.cccd for r in b_bca]


def test_clean_dataset_passes_pipeline():
    ocr_map, bca_recs = generate(n_citizens=5, seed=7)
    bca = BCADatabase(bca_recs)
    engine = MockOCREngine(ocr_map)
    for image in ocr_map:
        result = process_image(image, ocr=engine, bca=bca)
        assert result.validation.is_valid


def test_name_mismatch_anomaly_fails_pipeline():
    ocr_map, bca_recs = generate(n_citizens=2, seed=1, anomalies=["name_mismatch"])
    bca = BCADatabase(bca_recs)
    engine = MockOCREngine(ocr_map)
    failures = 0
    for image in ocr_map:
        if not process_image(image, ocr=engine, bca=bca).validation.is_valid:
            failures += 1
    assert failures >= 1


def test_dob_mismatch_anomaly_fails_pipeline():
    ocr_map, bca_recs = generate(n_citizens=2, seed=1, anomalies=["dob_mismatch"])
    bca = BCADatabase(bca_recs)
    engine = MockOCREngine(ocr_map)
    failures = 0
    for image in ocr_map:
        if not process_image(image, ocr=engine, bca=bca).validation.is_valid:
            failures += 1
    assert failures >= 1


def test_gender_mismatch_anomaly_fails_pipeline():
    ocr_map, bca_recs = generate(n_citizens=2, seed=1, anomalies=["gender_mismatch"])
    bca = BCADatabase(bca_recs)
    engine = MockOCREngine(ocr_map)
    failures = 0
    for image in ocr_map:
        if not process_image(image, ocr=engine, bca=bca).validation.is_valid:
            failures += 1
    assert failures >= 1


def test_not_in_bca_anomaly_fails_pipeline():
    ocr_map, bca_recs = generate(n_citizens=2, seed=1, anomalies=["not_in_bca"])
    bca = BCADatabase(bca_recs)
    engine = MockOCREngine(ocr_map)
    failures = 0
    for image in ocr_map:
        if not process_image(image, ocr=engine, bca=bca).validation.is_valid:
            failures += 1
    assert failures >= 1


def test_bad_cccd_anomaly_fails_pipeline():
    ocr_map, bca_recs = generate(n_citizens=2, seed=1, anomalies=["bad_cccd"])
    bca = BCADatabase(bca_recs)
    engine = MockOCREngine(ocr_map)
    failures = 0
    for image in ocr_map:
        if not process_image(image, ocr=engine, bca=bca).validation.is_valid:
            failures += 1
    assert failures >= 1


def test_unknown_anomaly_kind_raises():
    with pytest.raises(ValueError):
        generate(n_citizens=1, anomalies=["meteor_strike"])
