"""multi-source-collector — HTTP / CSV / Excel / FTP / GSheet → staging zone."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "NamingConvention": ("msc.naming", "NamingConvention"),
        "StagedKey": ("msc.naming", "StagedKey"),
        "Manifest": ("msc.manifest", "Manifest"),
        "ManifestEntry": ("msc.manifest", "ManifestEntry"),
        "Source": ("msc.sources.base", "Source"),
        "SourceError": ("msc.sources.base", "SourceError"),
        "Record": ("msc.sources.base", "Record"),
        "CSVSource": ("msc.sources.csv_src", "CSVSource"),
        "ExcelSource": ("msc.sources.excel", "ExcelSource"),
        "HTTPAPISource": ("msc.sources.http_api", "HTTPAPISource"),
        "FTPSource": ("msc.sources.ftp", "FTPSource"),
        "GoogleSheetSource": ("msc.sources.gsheet", "GoogleSheetSource"),
        "StagingZone": ("msc.staging.zone", "StagingZone"),
        "Runner": ("msc.runner", "Runner"),
        "IngestionResult": ("msc.runner", "IngestionResult"),
    }

    if name in _LAZY:
        from importlib import import_module

        module, attr = _LAZY[name]
        return getattr(import_module(module), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "CSVSource",
    "ExcelSource",
    "FTPSource",
    "GoogleSheetSource",
    "HTTPAPISource",
    "IngestionResult",
    "Manifest",
    "ManifestEntry",
    "NamingConvention",
    "Record",
    "Runner",
    "Source",
    "SourceError",
    "StagedKey",
    "StagingZone",
    "__version__",
]
