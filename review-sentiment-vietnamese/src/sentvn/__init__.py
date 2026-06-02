"""review-sentiment-vietnamese — VN review sentiment pipeline."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Bucket": ("sentvn.aggregations", "Bucket"),
        "INTENSIFIERS": ("sentvn.lexicon", "INTENSIFIERS"),
        "LexiconClassifier": ("sentvn.classifier", "LexiconClassifier"),
        "NEGATIVE_WORDS": ("sentvn.lexicon", "NEGATIVE_WORDS"),
        "NEGATORS": ("sentvn.lexicon", "NEGATORS"),
        "POSITIVE_WORDS": ("sentvn.lexicon", "POSITIVE_WORDS"),
        "Review": ("sentvn.schema", "Review"),
        "SentimentClassifier": ("sentvn.classifier", "SentimentClassifier"),
        "SentimentLabel": ("sentvn.schema", "SentimentLabel"),
        "SentimentResult": ("sentvn.schema", "SentimentResult"),
        "VN_TZ": ("sentvn.schema", "VN_TZ"),
        "by_category": ("sentvn.aggregations", "by_category"),
        "by_product": ("sentvn.aggregations", "by_product"),
        "by_seller": ("sentvn.aggregations", "by_seller"),
        "dump_results": ("sentvn.io_jsonl", "dump_results"),
        "dump_reviews": ("sentvn.io_jsonl", "dump_reviews"),
        "generate": ("sentvn.simulator", "generate"),
        "load_results": ("sentvn.io_jsonl", "load_results"),
        "load_reviews": ("sentvn.io_jsonl", "load_reviews"),
        "normalize_vn_text": ("sentvn.lexicon", "normalize_vn_text"),
        "result_from_dict": ("sentvn.io_jsonl", "result_from_dict"),
        "result_to_dict": ("sentvn.io_jsonl", "result_to_dict"),
        "review_from_dict": ("sentvn.io_jsonl", "review_from_dict"),
        "review_to_dict": ("sentvn.io_jsonl", "review_to_dict"),
        "score_text": ("sentvn.classifier", "score_text"),
        "score_to_label": ("sentvn.classifier", "score_to_label"),
        "tokenize": ("sentvn.lexicon", "tokenize"),
        "top_n": ("sentvn.aggregations", "top_n"),
        "worst_n": ("sentvn.aggregations", "worst_n"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "INTENSIFIERS",
    "NEGATIVE_WORDS",
    "NEGATORS",
    "POSITIVE_WORDS",
    "VN_TZ",
    "Bucket",
    "LexiconClassifier",
    "Review",
    "SentimentClassifier",
    "SentimentLabel",
    "SentimentResult",
    "__version__",
    "by_category",
    "by_product",
    "by_seller",
    "dump_results",
    "dump_reviews",
    "generate",
    "load_results",
    "load_reviews",
    "normalize_vn_text",
    "result_from_dict",
    "result_to_dict",
    "review_from_dict",
    "review_to_dict",
    "score_text",
    "score_to_label",
    "tokenize",
    "top_n",
    "worst_n",
]
