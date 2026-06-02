"""Input string normalisation — diacritic folding + abbreviation expansion.

The goal: make raw VN address tokens comparable to canonical unit
names regardless of how the user typed them.

Operations applied in order:

1. **Strip + lowercase** — case-insensitive matching.
2. **Expand abbreviations** — ``q.1``/``q1`` → ``quận 1``,
   ``tp.hcm``/``tphcm`` → ``thành phố hồ chí minh``,
   ``p.bến nghé``/``p1`` → ``phường …``.
3. **Fold diacritics** — ``hồ chí minh`` → ``ho chi minh``. Two
   strings are then comparable even if the user dropped accent
   marks (very common in VN web forms).
4. **Collapse whitespace** — multiple spaces / tabs → one space.

The helper functions are exposed for use by the parser; the
top-level ``normalise()`` runs the full pipeline.
"""

from __future__ import annotations

import re
import unicodedata

# ---- Diacritic-folding table -----------------------------------------------

_VN_MAP = {
    # a
    "à": "a",
    "á": "a",
    "ả": "a",
    "ã": "a",
    "ạ": "a",
    "ă": "a",
    "ằ": "a",
    "ắ": "a",
    "ẳ": "a",
    "ẵ": "a",
    "ặ": "a",
    "â": "a",
    "ầ": "a",
    "ấ": "a",
    "ẩ": "a",
    "ẫ": "a",
    "ậ": "a",
    # e
    "è": "e",
    "é": "e",
    "ẻ": "e",
    "ẽ": "e",
    "ẹ": "e",
    "ê": "e",
    "ề": "e",
    "ế": "e",
    "ể": "e",
    "ễ": "e",
    "ệ": "e",
    # i
    "ì": "i",
    "í": "i",
    "ỉ": "i",
    "ĩ": "i",
    "ị": "i",
    # o
    "ò": "o",
    "ó": "o",
    "ỏ": "o",
    "õ": "o",
    "ọ": "o",
    "ô": "o",
    "ồ": "o",
    "ố": "o",
    "ổ": "o",
    "ỗ": "o",
    "ộ": "o",
    "ơ": "o",
    "ờ": "o",
    "ớ": "o",
    "ở": "o",
    "ỡ": "o",
    "ợ": "o",
    # u
    "ù": "u",
    "ú": "u",
    "ủ": "u",
    "ũ": "u",
    "ụ": "u",
    "ư": "u",
    "ừ": "u",
    "ứ": "u",
    "ử": "u",
    "ữ": "u",
    "ự": "u",
    # y
    "ỳ": "y",
    "ý": "y",
    "ỷ": "y",
    "ỹ": "y",
    "ỵ": "y",
    # d
    "đ": "d",
}


def fold_diacritics(text: str) -> str:
    """Replace VN diacritics with their ASCII equivalents.

    Lower-cases first so the mapping is consistent. Uses NFC
    normalisation so combining marks coalesce before lookup.
    """
    text = unicodedata.normalize("NFC", text.lower())
    out_chars: list[str] = []
    for ch in text:
        out_chars.append(_VN_MAP.get(ch, ch))
    return "".join(out_chars)


# ---- Abbreviation expansion ------------------------------------------------

# Order matters: longer/more-specific patterns first so they don't get
# eaten by their shorter prefixes (e.g. ``tphcm`` before ``tp``).
_ABBREV_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # City / province
    (re.compile(r"\btp\.?\s*hcm\b", re.IGNORECASE), "thành phố hồ chí minh"),
    (re.compile(r"\btphcm\b", re.IGNORECASE), "thành phố hồ chí minh"),
    (re.compile(r"\bt\.?p\.?\s+hồ\s+chí\s+minh\b", re.IGNORECASE), "thành phố hồ chí minh"),
    (re.compile(r"\btp\.?\s*hn\b", re.IGNORECASE), "thành phố hà nội"),
    (re.compile(r"\btp\.?\s*đn\b", re.IGNORECASE), "thành phố đà nẵng"),
    (re.compile(r"\btp\.?\s*hp\b", re.IGNORECASE), "thành phố hải phòng"),
    (re.compile(r"\btp\.?\s*ct\b", re.IGNORECASE), "thành phố cần thơ"),
    # Generic district abbreviations
    (re.compile(r"\bq\.?\s*(\d+)\b", re.IGNORECASE), r"quận \1"),
    (re.compile(r"\bquan\s+(\d+)\b", re.IGNORECASE), r"quận \1"),
    (re.compile(r"\bh\.?\s+", re.IGNORECASE), "huyện "),
    (re.compile(r"\btx\.?\s+", re.IGNORECASE), "thị xã "),
    (re.compile(r"\btt\.?\s+", re.IGNORECASE), "thị trấn "),
    (re.compile(r"\btỉnh\.?\s+", re.IGNORECASE), "tỉnh "),
    # Ward
    (re.compile(r"\bp\.?\s*(\d+)\b", re.IGNORECASE), r"phường \1"),
    (re.compile(r"\bp\.\s+", re.IGNORECASE), "phường "),
    (re.compile(r"\bxã\.?\s+", re.IGNORECASE), "xã "),
)


def expand_abbreviations(text: str) -> str:
    """Expand common VN address abbreviations to canonical forms."""
    out = text
    for pattern, replacement in _ABBREV_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


# ---- Pipeline --------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Run the full normalisation pipeline.

    The output is diacritic-folded lowercase ASCII with abbreviations
    expanded — suitable for direct comparison against
    ``fold_diacritics(unit.name_vi)``.
    """
    expanded = expand_abbreviations(text.strip().lower())
    folded = fold_diacritics(expanded)
    return _WHITESPACE_RE.sub(" ", folded).strip()


def tokens(text: str) -> list[str]:
    """Split a raw address on commas / slashes into trimmed tokens.

    Empty tokens are dropped. Newlines, tabs, and multi-space runs
    are collapsed within each token via ``normalise()``.
    """
    raw_parts = re.split(r"[,/]", text)
    return [p.strip() for p in raw_parts if p.strip()]


__all__ = [
    "expand_abbreviations",
    "fold_diacritics",
    "normalise",
    "tokens",
]
