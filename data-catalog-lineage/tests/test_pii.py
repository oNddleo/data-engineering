"""Tests for PII detector."""

from __future__ import annotations

from datacatalog.pii import PIIDetector
from datacatalog.schema import PIICategory


class TestPIIDetector:
    def setup_method(self) -> None:
        self.d = PIIDetector()

    def test_email_column_name(self) -> None:
        assert self.d.detect("email") == PIICategory.EMAIL

    def test_email_address_column_name(self) -> None:
        assert self.d.detect("email_address") == PIICategory.EMAIL

    def test_phone_column_name(self) -> None:
        assert self.d.detect("phone") == PIICategory.PHONE

    def test_mobile_column_name(self) -> None:
        assert self.d.detect("mobile") == PIICategory.PHONE

    def test_ssn_column_name(self) -> None:
        assert self.d.detect("ssn") == PIICategory.SSN

    def test_password_column_name(self) -> None:
        assert self.d.detect("password") == PIICategory.PASSWORD

    def test_first_name(self) -> None:
        assert self.d.detect("first_name") == PIICategory.NAME

    def test_last_name(self) -> None:
        assert self.d.detect("last_name") == PIICategory.NAME

    def test_dob(self) -> None:
        assert self.d.detect("dob") == PIICategory.DATE_OF_BIRTH

    def test_ip_address(self) -> None:
        assert self.d.detect("ip_address") == PIICategory.IP_ADDRESS

    def test_non_pii_column(self) -> None:
        assert self.d.detect("order_id") == PIICategory.NONE
        assert self.d.detect("total_amount") == PIICategory.NONE
        assert self.d.detect("created_at") == PIICategory.NONE

    def test_email_from_values(self) -> None:
        result = self.d.detect("user_field", ["foo@bar.com"])
        assert result == PIICategory.EMAIL

    def test_ssn_from_values(self) -> None:
        result = self.d.detect("field", ["123-45-6789"])
        assert result == PIICategory.SSN

    def test_scan_columns(self) -> None:
        cols = [
            ("email", None),
            ("phone", None),
            ("order_id", None),
        ]
        results = self.d.scan_columns(cols)
        assert results["email"] == PIICategory.EMAIL
        assert results["phone"] == PIICategory.PHONE
        assert results["order_id"] == PIICategory.NONE
