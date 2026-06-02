"""Vietnamese keyword normaliser + scam-dictionary tests."""

from __future__ import annotations

from fraudvn.keywords import (
    KEYWORD_CATEGORY_WEIGHTS,
    SCAM_KEYWORDS,
    find_scam_keywords,
    normalize_vn_text,
)


def test_normalize_strips_diacritics():
    assert normalize_vn_text("Công An") == "cong an"
    assert normalize_vn_text("CÔNG AN") == "cong an"
    assert normalize_vn_text("đầu tư") == "dau tu"
    assert normalize_vn_text("Việc nhẹ lương cao") == "viec nhe luong cao"


def test_normalize_preserves_ascii_lowercase():
    assert normalize_vn_text("hello world") == "hello world"


def test_normalize_handles_d_capital():
    assert normalize_vn_text("Đầu Tư") == "dau tu"


def test_find_scam_keywords_cong_an_in_full_narrative():
    out = find_scam_keywords("Chuyển khoản theo yêu cầu Công An phục vụ điều tra")
    assert "CONG_AN_IMPERSONATION" in out
    assert "cong an" in out["CONG_AN_IMPERSONATION"]


def test_find_scam_keywords_wrong_transfer():
    out = find_scam_keywords("Em chuyển nhầm, anh chuyển lại giúp em")
    assert "WRONG_TRANSFER_SCAM" in out


def test_find_scam_keywords_crypto():
    out = find_scam_keywords("Đầu tư crypto sàn ABC lợi nhuận cao")
    assert "CRYPTO_FOREX_SCAM" in out


def test_find_scam_keywords_job_scam():
    out = find_scam_keywords("Tuyển CTV online việc nhẹ lương cao")
    assert "JOB_SCAM" in out


def test_find_scam_keywords_loan_scam():
    out = find_scam_keywords("Vay tiền online không thế chấp")
    assert "LOAN_SCAM" in out


def test_find_scam_keywords_clean_narrative_returns_empty():
    assert find_scam_keywords("Tiền ăn trưa với đồng nghiệp") == {}


def test_find_scam_keywords_empty_input():
    assert find_scam_keywords("") == {}


def test_find_scam_keywords_can_fire_multiple_categories():
    out = find_scam_keywords("Đầu tư crypto vay nhanh không thế chấp")
    assert "CRYPTO_FOREX_SCAM" in out
    assert "LOAN_SCAM" in out


def test_keyword_category_weights_cover_all_categories():
    assert set(KEYWORD_CATEGORY_WEIGHTS.keys()) == set(SCAM_KEYWORDS.keys())


def test_keyword_weights_positive():
    for w in KEYWORD_CATEGORY_WEIGHTS.values():
        assert w > 0
