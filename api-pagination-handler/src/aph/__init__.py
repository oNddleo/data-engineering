"""api-pagination-handler — generic paginator + retry framework."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "PageRequest": ("aph.paginators.base", "PageRequest"),
        "Paginator": ("aph.paginators.base", "Paginator"),
        "OffsetPaginator": ("aph.paginators.offset", "OffsetPaginator"),
        "CursorPaginator": ("aph.paginators.cursor", "CursorPaginator"),
        "TokenPaginator": ("aph.paginators.token", "TokenPaginator"),
        "LinkHeaderPaginator": ("aph.paginators.link_header", "LinkHeaderPaginator"),
        "RetryPolicy": ("aph.retry", "RetryPolicy"),
        "RetryError": ("aph.retry", "RetryError"),
        "Response": ("aph.transport", "Response"),
        "PaginatedClient": ("aph.client", "PaginatedClient"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "CursorPaginator",
    "LinkHeaderPaginator",
    "OffsetPaginator",
    "PageRequest",
    "PaginatedClient",
    "Paginator",
    "Response",
    "RetryError",
    "RetryPolicy",
    "TokenPaginator",
    "__version__",
]
