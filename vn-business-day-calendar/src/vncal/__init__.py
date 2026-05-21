"""vn-business-day-calendar — VN public holidays + working-day arithmetic."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "FiscalYear": ("vncal.schema", "FiscalYear"),
        "Holiday": ("vncal.schema", "Holiday"),
        "HolidayKind": ("vncal.schema", "HolidayKind"),
        "VN_TZ": ("vncal.schema", "VN_TZ"),
        "add_business_days": ("vncal.calendar_ops", "add_business_days"),
        "april_march_fy": ("vncal.fiscal", "april_march_fy"),
        "build_year": ("vncal.holidays", "build_year"),
        "build_years": ("vncal.holidays", "build_years"),
        "business_days_between": ("vncal.calendar_ops", "business_days_between"),
        "calendar_fy": ("vncal.fiscal", "calendar_fy"),
        "dump_fiscal_years": ("vncal.io_jsonl", "dump_fiscal_years"),
        "dump_holidays": ("vncal.io_jsonl", "dump_holidays"),
        "fiscal_year_for": ("vncal.fiscal", "fiscal_year_for"),
        "fiscal_year_from_dict": ("vncal.io_jsonl", "fiscal_year_from_dict"),
        "fiscal_year_to_dict": ("vncal.io_jsonl", "fiscal_year_to_dict"),
        "gio_to_solar": ("vncal.lunar", "gio_to_solar"),
        "holiday_from_dict": ("vncal.io_jsonl", "holiday_from_dict"),
        "holiday_to_dict": ("vncal.io_jsonl", "holiday_to_dict"),
        "is_business_day": ("vncal.calendar_ops", "is_business_day"),
        "load_fiscal_years": ("vncal.io_jsonl", "load_fiscal_years"),
        "load_holidays": ("vncal.io_jsonl", "load_holidays"),
        "max_year": ("vncal.lunar", "max_year"),
        "min_year": ("vncal.lunar", "min_year"),
        "next_business_day": ("vncal.calendar_ops", "next_business_day"),
        "prev_business_day": ("vncal.calendar_ops", "prev_business_day"),
        "supported_years": ("vncal.lunar", "supported_years"),
        "tet_solar": ("vncal.lunar", "tet_solar"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "FiscalYear",
    "Holiday",
    "HolidayKind",
    "VN_TZ",
    "__version__",
    "add_business_days",
    "april_march_fy",
    "build_year",
    "build_years",
    "business_days_between",
    "calendar_fy",
    "dump_fiscal_years",
    "dump_holidays",
    "fiscal_year_for",
    "fiscal_year_from_dict",
    "fiscal_year_to_dict",
    "gio_to_solar",
    "holiday_from_dict",
    "holiday_to_dict",
    "is_business_day",
    "load_fiscal_years",
    "load_holidays",
    "max_year",
    "min_year",
    "next_business_day",
    "prev_business_day",
    "supported_years",
    "tet_solar",
]
