"""
EncryptionEngine — envelope-encrypt columns in plain dicts.

Envelope encryption flow:
  1. Generate a random 256-bit DEK for this record.
  2. Wrap the DEK under the customer's active CMK (via LocalKMS).
  3. Encrypt each PII column value with the DEK using HmacCtrCipher.
  4. Store wrapped DEK + per-column ciphertext in EncryptedRecord.

Decryption flow:
  1. Unwrap the DEK using the CMK stored on the record.
  2. Decrypt each encrypted column with the DEK.
  3. Return a plain dict merged with the untouched plaintext columns.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from colenc.cipher import HmacCtrCipher
from colenc.kms import LocalKMS
from colenc.storage import EncryptedRecord, RecordStore, b64_decode, b64_encode, new_record_id

DEFAULT_PII_COLUMNS: frozenset[str] = frozenset(
    ["ssn", "email", "phone", "dob", "full_name", "address", "ip_address"]
)


class EncryptionEngine:
    """Encrypt and decrypt column-level PII in records using envelope encryption."""

    def __init__(
        self,
        kms: LocalKMS | None = None,
        pii_columns: frozenset[str] | None = None,
    ) -> None:
        self._kms = kms or LocalKMS()
        self._cipher = HmacCtrCipher()
        self._pii_columns = pii_columns if pii_columns is not None else DEFAULT_PII_COLUMNS

    # ------------------------------------------------------------------
    # Encrypt
    # ------------------------------------------------------------------

    def encrypt_record(
        self,
        record: dict[str, Any],
        customer_id: str,
        columns: list[str] | None = None,
    ) -> EncryptedRecord:
        """Encrypt PII columns in *record* and return an :class:`EncryptedRecord`.

        Args:
            record: Plain dict of column name -> value.
            customer_id: Customer identifier used to look up the CMK.
            columns: Explicit list of columns to encrypt.  When *None* the
                     default PII column set is used.
        """
        pii_cols: frozenset[str] = frozenset(columns) if columns is not None else self._pii_columns

        cmk_id = self._kms.get_active_cmk(customer_id)
        dek = secrets.token_bytes(32)
        wrapped_dek_bytes = self._kms.wrap_dek(cmk_id, dek)

        encrypted_columns: dict[str, str] = {}
        plaintext_columns: dict[str, Any] = {}

        for col, value in record.items():
            if col in pii_cols and value is not None:
                payload = json.dumps(value).encode()
                ct_blob = self._cipher.encrypt(dek, payload)
                encrypted_columns[col] = b64_encode(ct_blob)
            else:
                plaintext_columns[col] = value

        return EncryptedRecord(
            record_id=new_record_id(),
            customer_id=customer_id,
            cmk_id=cmk_id,
            wrapped_dek=b64_encode(wrapped_dek_bytes),
            encrypted_columns=encrypted_columns,
            plaintext_columns=plaintext_columns,
        )

    # ------------------------------------------------------------------
    # Decrypt
    # ------------------------------------------------------------------

    def decrypt_record(
        self,
        encrypted_record: EncryptedRecord,
        columns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Decrypt an :class:`EncryptedRecord` and return the original plain dict.

        Args:
            encrypted_record: The record to decrypt.
            columns: If provided, only decrypt these columns; others in
                     ``encrypted_columns`` are silently skipped.
        """
        wrapped_dek_bytes = b64_decode(encrypted_record.wrapped_dek)
        dek = self._kms.unwrap_dek(encrypted_record.cmk_id, wrapped_dek_bytes)

        cols_to_decrypt = (
            frozenset(columns)
            if columns is not None
            else frozenset(encrypted_record.encrypted_columns)
        )

        result: dict[str, Any] = dict(encrypted_record.plaintext_columns)
        for col, ct_b64 in encrypted_record.encrypted_columns.items():
            if col not in cols_to_decrypt:
                continue
            ct_blob = b64_decode(ct_b64)
            payload = self._cipher.decrypt(dek, ct_blob)
            result[col] = json.loads(payload.decode())

        return result

    # ------------------------------------------------------------------
    # Re-encrypt (key rotation — re-wrap DEK only, column ciphertext unchanged)
    # ------------------------------------------------------------------

    def re_encrypt_record(
        self,
        encrypted_record: EncryptedRecord,
        new_cmk_id: str,
    ) -> EncryptedRecord:
        """Re-wrap the DEK under *new_cmk_id*.

        The column ciphertext is unchanged — only the envelope key changes.
        This is O(1) regardless of column data size.
        """
        old_cmk_id = encrypted_record.cmk_id
        wrapped_dek_bytes = b64_decode(encrypted_record.wrapped_dek)
        dek = self._kms.unwrap_dek(old_cmk_id, wrapped_dek_bytes)
        new_wrapped_dek_bytes = self._kms.wrap_dek(new_cmk_id, dek)

        return EncryptedRecord(
            record_id=encrypted_record.record_id,
            customer_id=encrypted_record.customer_id,
            cmk_id=new_cmk_id,
            wrapped_dek=b64_encode(new_wrapped_dek_bytes),
            encrypted_columns=dict(encrypted_record.encrypted_columns),
            plaintext_columns=dict(encrypted_record.plaintext_columns),
            created_at=encrypted_record.created_at,
        )

    # ------------------------------------------------------------------
    # Convenience: encrypt_and_store / load_and_decrypt
    # ------------------------------------------------------------------

    def encrypt_and_store(
        self,
        record: dict[str, Any],
        customer_id: str,
        store: RecordStore,
        columns: list[str] | None = None,
    ) -> EncryptedRecord:
        """Encrypt *record* and persist it in *store*."""
        enc = self.encrypt_record(record, customer_id, columns)
        store.put(enc)
        return enc

    def load_and_decrypt(
        self,
        record_id: str,
        store: RecordStore,
        columns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Load a record from *store* and decrypt it."""
        enc = store.get(record_id)
        return self.decrypt_record(enc, columns)
