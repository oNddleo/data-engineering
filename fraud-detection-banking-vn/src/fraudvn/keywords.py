"""Vietnamese scam-keyword dictionaries + diacritic-stripping normaliser.

Vietnamese uses both combining diacritics (acute, grave, hook, tilde,
dot-below) **and** one truly distinct letter — ``đ``/``Đ`` — that
NFD doesn't decompose. To match scam keywords robustly across all
of *Công An*, *cong an*, *CÔNG AN*, *Công an*, etc., we normalise
both the narrative and the keyword to ASCII lower-case before
substring matching:

1. Replace ``đ`` / ``Đ`` → ``d``.
2. ``unicodedata.normalize("NFD", text)`` decomposes the rest.
3. Strip combining characters.
4. Lower-case.

The dictionaries below are curated from the State Bank of Vietnam's
public fraud-warning advisories and Bộ Công An press releases —
they're the five most common scam categories targeting retail
banking customers in 2024–2025.
"""

from __future__ import annotations

import unicodedata


def normalize_vn_text(text: str) -> str:
    """Strip Vietnamese diacritics + lower-case for keyword matching.

    Handles ``đ`` / ``Đ`` explicitly since NFD doesn't decompose them.
    """
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if not unicodedata.combining(c))
    return stripped.lower()


# ---------------------------------------------------------------------------
# Scam categories. Each value is the *plain ASCII* form of the keyword —
# the matcher normalises the narrative before comparing.


SCAM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "CONG_AN_IMPERSONATION": (
        "cong an",
        "dieu tra",
        "vien kiem sat",
        "toa an",
        "lenh bat",
        "khoi to",
        "vu an",
    ),
    "WRONG_TRANSFER_SCAM": (
        "chuyen nham",
        "hoan lai",
        "gui lai",
        "tra lai",
        "chuyen lai",
    ),
    "CRYPTO_FOREX_SCAM": (
        "crypto",
        "bitcoin",
        "forex",
        "san dau tu",
        "loi nhuan cao",
        "dau tu sieu loi nhuan",
    ),
    "JOB_SCAM": (
        "viec nhe luong cao",
        "tuyen ctv",
        "tuyen cong tac vien",
        "ctv online",
        "viec lam online",
        "lam viec tai nha luong cao",
    ),
    "LOAN_SCAM": (
        "vay nhanh",
        "vay tien online",
        "vay khong the chap",
        "app vay tien",
        "vay nong",
    ),
}
"""Map ``category → tuple of plain-ASCII keyword phrases``."""


KEYWORD_CATEGORY_WEIGHTS: dict[str, int] = {
    "CONG_AN_IMPERSONATION": 55,
    "WRONG_TRANSFER_SCAM": 35,
    "CRYPTO_FOREX_SCAM": 40,
    "JOB_SCAM": 30,
    "LOAN_SCAM": 25,
}


def find_scam_keywords(narrative: str) -> dict[str, list[str]]:
    """Return matched ``{category: [keyword,...]}`` for a transaction narrative.

    Empty if nothing matched. Caller can compute total points by
    summing :data:`KEYWORD_CATEGORY_WEIGHTS` for the returned keys.
    """
    if not narrative:
        return {}
    norm = normalize_vn_text(narrative)
    out: dict[str, list[str]] = {}
    for cat, kws in SCAM_KEYWORDS.items():
        hits = [k for k in kws if k in norm]
        if hits:
            out[cat] = hits
    return out


__all__ = [
    "KEYWORD_CATEGORY_WEIGHTS",
    "SCAM_KEYWORDS",
    "find_scam_keywords",
    "normalize_vn_text",
]
