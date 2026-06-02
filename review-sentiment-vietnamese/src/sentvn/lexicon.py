"""Vietnamese sentiment lexicon — single-token entries after diacritic stripping.

We keep the lexicon **in ASCII** form: the classifier normalises the
input before comparing (same approach as
[`fraud-detection-banking-vn`](../../fraud-detection-banking-vn/)).
That way ``Tốt``, ``tot``, ``TỐT`` all match the same entry.

The four word classes:

* **Positive** — add ``+1`` to the running sentiment score.
* **Negative** — add ``−1``.
* **Intensifiers** — multiply the *next* sentiment word's
  contribution by ``2.0``.
* **Negators** — flip the sign of the *next* sentiment word.

Negators + intensifiers combine: ``rất không tốt`` →
intensify (× 2) + negate → ``+1`` flipped + ×2 = ``−2``.

These dictionaries are deliberately small — only high-confidence
words that don't depend on context to mean what they say. A
production deployment would expand the lexicon from labelled
Shopee / Lazada / Tiki review datasets, or skip this approach
entirely and use PhoBERT / VinAI via the ``SentimentClassifier``
Protocol.
"""

from __future__ import annotations

import unicodedata

POSITIVE_WORDS: frozenset[str] = frozenset(
    {
        "tot",  # tốt — good
        "tuyet",  # tuyệt — wonderful
        "dep",  # đẹp — beautiful
        "ngon",  # ngon — delicious
        "nhanh",  # nhanh — fast
        "re",  # rẻ — cheap
        "ben",  # bền — durable
        "manh",  # mạnh — strong
        "dinh",  # đỉnh — top
        "xinh",  # xinh — pretty
        "thich",  # thích — like
        "ung",  # ưng — satisfied
        "yeu",  # yêu — love
        "hay",  # hay — good (informal)
        "ngot",  # ngọt — sweet
        "muot",  # mượt — smooth
        "chuan",  # chuẩn — standard / correct
        "okela",  # okela — informal "okay"
    }
)

NEGATIVE_WORDS: frozenset[str] = frozenset(
    {
        "te",  # tệ — bad
        "kem",  # kém — poor
        "cham",  # chậm — slow
        "hong",  # hỏng — broken
        "do",  # dở — bad
        "gia",  # giả — fake
        "xau",  # xấu — ugly
        "dat",  # đắt — expensive (negative connotation)
        "chan",  # chán — boring
        "lua",  # lừa — scam
        "bun",  # bùn — bad (slang)
        "ghet",  # ghét — hate
        "phi",  # phí — wasted
        "tham",  # thâm — bad (about quality)
        "loi",  # lỗi — defective
        "rach",  # rách — torn
        "ban",  # bẩn — dirty
    }
)

INTENSIFIERS: frozenset[str] = frozenset(
    {
        "rat",  # rất — very
        "cuc",  # cực — extremely
        "sieu",  # siêu — super
        "qua",  # quá — too
        "that",  # thật — really
        "khong_the",  # không thể — utterly
    }
)

NEGATORS: frozenset[str] = frozenset(
    {
        "khong",  # không — not
        "chang",  # chẳng — not (literary)
        "chua",  # chưa — not yet
        "deu",  # đếu — not at all (informal)
        "dau",  # đâu — not at all (colloquial)
    }
)


def normalize_vn_text(text: str) -> str:
    """Strip Vietnamese diacritics + lower-case for lexicon matching.

    Handles ``đ`` / ``Đ`` explicitly since NFD doesn't decompose them.
    """
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if not unicodedata.combining(c))
    return stripped.lower()


def tokenize(text: str) -> list[str]:
    """Tokenise on whitespace + punctuation. ASCII output (caller pre-normalised)."""
    norm = normalize_vn_text(text) if any(ord(c) > 127 for c in text) else text.lower()
    out: list[str] = []
    current: list[str] = []
    for ch in norm:
        if ch.isalnum() or ch == "_":
            current.append(ch)
        else:
            if current:
                out.append("".join(current))
                current = []
    if current:
        out.append("".join(current))
    return out


__all__ = [
    "INTENSIFIERS",
    "NEGATIVE_WORDS",
    "NEGATORS",
    "POSITIVE_WORDS",
    "normalize_vn_text",
    "tokenize",
]
