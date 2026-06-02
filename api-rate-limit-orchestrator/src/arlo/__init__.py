"""api-rate-limit-orchestrator — distributed token-bucket rate limiter."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Quota": ("arlo.quota", "Quota"),
        "StorageBackend": ("arlo.storage.base", "StorageBackend"),
        "InMemoryStorage": ("arlo.storage.inmemory", "InMemoryStorage"),
        "TokenBucket": ("arlo.bucket", "TokenBucket"),
        "AcquireResult": ("arlo.bucket", "AcquireResult"),
        "Orchestrator": ("arlo.orchestrator", "Orchestrator"),
        "REDIS_TOKEN_BUCKET_LUA": ("arlo.storage.redis_lua", "REDIS_TOKEN_BUCKET_LUA"),
        "render_redis_lua": ("arlo.storage.redis_lua", "render_redis_lua"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "REDIS_TOKEN_BUCKET_LUA",
    "AcquireResult",
    "InMemoryStorage",
    "Orchestrator",
    "Quota",
    "StorageBackend",
    "TokenBucket",
    "__version__",
    "render_redis_lua",
]
