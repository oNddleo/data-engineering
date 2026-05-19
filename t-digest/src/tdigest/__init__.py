"""t-digest — streaming quantile sketch (Dunning 2014)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from tdigest.digest import (
        add,
        build,
        cdf,
        compress,
        freeze,
        merge,
        quantile,
        thaw,
    )
    from tdigest.io_jsonl import (
        digest_from_dict,
        digest_to_dict,
        dump_digests,
        load_digests,
    )
    from tdigest.scale import k, max_combined_weight, q_from_k
    from tdigest.schema import BuildableTDigest, Centroid, TDigest
    from tdigest.simulator import (
        exact_quantile,
        gaussian_stream,
        lognormal_stream,
        pareto_stream,
        uniform_stream,
    )


_LAZY: dict[str, tuple[str, str]] = {
    "BuildableTDigest": ("tdigest.schema", "BuildableTDigest"),
    "Centroid": ("tdigest.schema", "Centroid"),
    "TDigest": ("tdigest.schema", "TDigest"),
    "add": ("tdigest.digest", "add"),
    "build": ("tdigest.digest", "build"),
    "cdf": ("tdigest.digest", "cdf"),
    "compress": ("tdigest.digest", "compress"),
    "digest_from_dict": ("tdigest.io_jsonl", "digest_from_dict"),
    "digest_to_dict": ("tdigest.io_jsonl", "digest_to_dict"),
    "dump_digests": ("tdigest.io_jsonl", "dump_digests"),
    "exact_quantile": ("tdigest.simulator", "exact_quantile"),
    "freeze": ("tdigest.digest", "freeze"),
    "gaussian_stream": ("tdigest.simulator", "gaussian_stream"),
    "k": ("tdigest.scale", "k"),
    "load_digests": ("tdigest.io_jsonl", "load_digests"),
    "lognormal_stream": ("tdigest.simulator", "lognormal_stream"),
    "max_combined_weight": ("tdigest.scale", "max_combined_weight"),
    "merge": ("tdigest.digest", "merge"),
    "pareto_stream": ("tdigest.simulator", "pareto_stream"),
    "q_from_k": ("tdigest.scale", "q_from_k"),
    "quantile": ("tdigest.digest", "quantile"),
    "thaw": ("tdigest.digest", "thaw"),
    "uniform_stream": ("tdigest.simulator", "uniform_stream"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BuildableTDigest",
    "Centroid",
    "TDigest",
    "__version__",
    "add",
    "build",
    "cdf",
    "compress",
    "digest_from_dict",
    "digest_to_dict",
    "dump_digests",
    "exact_quantile",
    "freeze",
    "gaussian_stream",
    "k",
    "load_digests",
    "lognormal_stream",
    "max_combined_weight",
    "merge",
    "pareto_stream",
    "q_from_k",
    "quantile",
    "thaw",
    "uniform_stream",
]
