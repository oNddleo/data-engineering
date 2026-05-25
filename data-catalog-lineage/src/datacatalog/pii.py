"""Pattern-based PII detector for column names and sample values."""

from __future__ import annotations

import re

from datacatalog.schema import PIICategory

# ── Name patterns ─────────────────────────────────────────────────────────────

_NAME_PATTERNS: list[tuple[PIICategory, re.Pattern[str]]] = [
    (PIICategory.EMAIL, re.compile(r"\b(email|e_mail|email_address|mail)\b", re.I)),
    (PIICategory.PHONE, re.compile(r"\b(phone|mobile|cell|telephone|tel)\b", re.I)),
    (PIICategory.SSN, re.compile(r"\b(ssn|social_security|sin)\b", re.I)),
    (PIICategory.CREDIT_CARD, re.compile(r"\b(cc_number|credit_card|card_num|pan)\b", re.I)),
    (
        PIICategory.NAME,
        re.compile(r"\b(first_name|last_name|full_name|given_name|surname)\b", re.I),
    ),
    (
        PIICategory.ADDRESS,
        re.compile(
            r"\b(address|street|city|zip|postal|postcode|lat|lng|latitude|longitude)\b",
            re.I,
        ),
    ),
    (PIICategory.DATE_OF_BIRTH, re.compile(r"\b(dob|date_of_birth|birth_date|birthdate)\b", re.I)),
    (PIICategory.IP_ADDRESS, re.compile(r"\b(ip_address|ip_addr|ipv4|ipv6)\b", re.I)),
    (PIICategory.PASSWORD, re.compile(r"\b(password|passwd|pwd|secret|token|api_key)\b", re.I)),
    (PIICategory.NATIONAL_ID, re.compile(r"\b(national_id|nid|citizen_id|id_number)\b", re.I)),
    (PIICategory.PASSPORT, re.compile(r"\b(passport|passport_num|passport_no)\b", re.I)),
    (PIICategory.BANK_ACCOUNT, re.compile(r"\b(bank_account|account_num|iban|routing)\b", re.I)),
    (
        PIICategory.HEALTH,
        re.compile(r"\b(diagnosis|condition|icd|medication|prescription|patient)\b", re.I),
    ),
    (PIICategory.BIOMETRIC, re.compile(r"\b(fingerprint|retina|face_id|biometric)\b", re.I)),
]

# ── Value patterns ────────────────────────────────────────────────────────────

_VALUE_PATTERNS: list[tuple[PIICategory, re.Pattern[str]]] = [
    (PIICategory.EMAIL, re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    (PIICategory.SSN, re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),  # before PHONE
    (PIICategory.IP_ADDRESS, re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
    (PIICategory.CREDIT_CARD, re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    (PIICategory.PHONE, re.compile(r"\+?[\d\s\-().]{7,15}")),
]


class PIIDetector:
    """Detects PII category from column name and optional sample values."""

    def detect(self, column_name: str, sample_values: list[str] | None = None) -> PIICategory:
        """Return the PII category for the given column name."""
        # Check name patterns first (higher confidence)
        for category, pattern in _NAME_PATTERNS:
            if pattern.search(column_name):
                return category

        # Check value patterns on samples
        if sample_values:
            for value in sample_values[:10]:  # check at most 10 samples
                for category, pattern in _VALUE_PATTERNS:
                    if pattern.search(str(value)):
                        return category

        return PIICategory.NONE

    def scan_columns(self, columns: list[tuple[str, list[str] | None]]) -> dict[str, PIICategory]:
        """Scan a list of (column_name, sample_values) pairs.

        Returns {column_name: PIICategory}.
        """
        return {name: self.detect(name, samples) for name, samples in columns}
