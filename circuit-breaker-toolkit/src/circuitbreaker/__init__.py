"""Circuit breaker resilience pattern."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "CircuitBreaker": ("circuitbreaker.breaker", "CircuitBreaker"),
        "CircuitBreakerConfig": ("circuitbreaker.breaker", "CircuitBreakerConfig"),
        "State": ("circuitbreaker.breaker", "State"),
        "CircuitOpenError": ("circuitbreaker.breaker", "CircuitOpenError"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = ["CircuitBreaker", "CircuitBreakerConfig", "State", "CircuitOpenError"]
