"""multi-tenant-ingestion-platform — quota-bounded multi-tenant ingestion."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Tenant": ("mtip.registry.tenant", "Tenant"),
        "TenantRegistry": ("mtip.registry.tenant", "TenantRegistry"),
        "ResourceQuota": ("mtip.quota", "ResourceQuota"),
        "ResourceUsage": ("mtip.quota", "ResourceUsage"),
        "SourceSpec": ("mtip.registry.source", "SourceSpec"),
        "SourceRegistry": ("mtip.registry.source", "SourceRegistry"),
        "StorageNamespace": ("mtip.isolation.storage", "StorageNamespace"),
        "ComputeSlots": ("mtip.isolation.compute", "ComputeSlots"),
        "AdmissionController": ("mtip.admission", "AdmissionController"),
        "Decision": ("mtip.admission", "Decision"),
        "Job": ("mtip.scheduler", "Job"),
        "Scheduled": ("mtip.scheduler", "Scheduled"),
        "FairScheduler": ("mtip.scheduler", "FairScheduler"),
        "Platform": ("mtip.platform", "Platform"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AdmissionController",
    "ComputeSlots",
    "Decision",
    "FairScheduler",
    "Job",
    "Platform",
    "ResourceQuota",
    "ResourceUsage",
    "Scheduled",
    "SourceRegistry",
    "SourceSpec",
    "StorageNamespace",
    "Tenant",
    "TenantRegistry",
    "__version__",
]
