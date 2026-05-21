"""Probabilistic watermarks for out-of-order stream processing.

Public API:
    from pwm import PerKeyDelayEstimator, WatermarkAdvancer, CorrectionStream
"""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "TDigest": "pwm.sketch.tdigest",
        "PerKeyDelayEstimator": "pwm.watermark.estimator",
        "WatermarkAdvancer": "pwm.watermark.advancer",
        "CorrectionStream": "pwm.correction.stream",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'pwm' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)


__all__ = ["CorrectionStream", "PerKeyDelayEstimator", "TDigest", "WatermarkAdvancer"]
