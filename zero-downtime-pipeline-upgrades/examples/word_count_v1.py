"""
Example pipeline v1 — basic word-count with a simple tokeniser.
"""

from typing import Any

from pipeline_deployer import BasePipeline


class WordCountV1(BasePipeline):
    """
    Counts words per document using a naive whitespace split.
    Maintains a running total of all words seen (stateful).
    """

    @property
    def version(self) -> str:
        return "v1.0.0"

    def setup(self) -> None:
        self._total_words = 0
        self._doc_count = 0

    def process(self, record: dict[str, Any]) -> dict[str, Any]:
        text: str = record.get("text", "")
        # naive split — does not strip punctuation
        tokens = text.split()
        word_count = len(tokens)

        self._total_words += word_count
        self._doc_count += 1

        return {
            "doc_id": record.get("doc_id"),
            "word_count": word_count,
            "running_total": self._total_words,
            "avg_words_per_doc": self._total_words / self._doc_count,
        }

    def snapshot_state(self) -> dict[str, Any]:
        return {"total_words": self._total_words, "doc_count": self._doc_count}

    def restore_state(self, snapshot: dict[str, Any]) -> None:
        self._total_words = snapshot.get("total_words", 0)
        self._doc_count = snapshot.get("doc_count", 0)
