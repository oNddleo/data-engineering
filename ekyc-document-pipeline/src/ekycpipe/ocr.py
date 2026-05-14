"""OCR Protocol + a deterministic mock engine for testing.

We **don't** bundle PaddleOCR / VietOCR — they're heavy
ML-stack dependencies that would dwarf this codebase. Instead we
define an ``OCREngine`` Protocol so callers can plug in:

* their PaddleOCR / VietOCR / Tesseract wrapper in production
* :class:`MockOCREngine` in tests (canned responses keyed by image bytes)

The contract is narrow: take ``image: bytes``, return an
:class:`OCRResult` with however many fields the engine could
recognise. The pipeline doesn't care which engine produced the
result — it just applies the same validation + cross-check rules.
"""

from __future__ import annotations

from typing import Protocol

from ekycpipe.schema import OCRResult


class OCREngine(Protocol):
    """Any object with a ``recognize(image) -> OCRResult`` method."""

    def recognize(self, image: bytes) -> OCRResult: ...


class MockOCREngine:
    """Looks up canned ``OCRResult`` by exact ``image`` bytes match.

    Useful when you have a fixed test set: register the expected
    result for each image identifier (raw bytes), and the pipeline
    sees the same engine surface as production.
    """

    def __init__(self, responses: dict[bytes, OCRResult]) -> None:
        self._responses = dict(responses)

    @property
    def size(self) -> int:
        return len(self._responses)

    def register(self, image: bytes, result: OCRResult) -> None:
        self._responses[image] = result

    def recognize(self, image: bytes) -> OCRResult:
        if image in self._responses:
            return self._responses[image]
        # Unknown image → engine returns an all-None result (the
        # pipeline will then fail with "OCR did not recognise CCCD").
        return OCRResult(
            cccd=None,
            full_name=None,
            date_of_birth=None,
            gender=None,
            hometown=None,
            place_of_residence=None,
            issued_at=None,
            expires_at=None,
            confidence=0.0,
        )


__all__ = ["MockOCREngine", "OCREngine"]
