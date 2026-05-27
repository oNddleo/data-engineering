"""
Local KMS — in-memory Customer Master Key (CMK) store.

Uses HMAC-SHA256-based key-wrap so no third-party crypto library is needed:

    wrapped_dek = HMAC-SHA256(cmk, dek + b'\\x01') XOR dek

The wrap is deterministic given the same CMK and DEK, but since each DEK is
random the wrapped value is effectively random too.  The MAC tag embedded in
the XOR construction provides authenticity: an attacker who flips bits in the
wrapped value will produce a DEK that fails the HMAC check in ``unwrap_dek``.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid


class KeyNotFoundError(Exception):
    """Raised when a requested CMK does not exist in the store."""


class KeyDeletedError(Exception):
    """Raised when trying to use a CMK that has been deleted (crypto-shredded)."""


def _hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b, strict=False))


class LocalKMS:
    """
    In-memory Local KMS for envelope encryption.

    Responsibilities:
    - Generate and store CMKs (256-bit random keys).
    - Wrap DEKs: ``HMAC-SHA256(cmk, dek + b'\\x01') XOR dek``.
    - Unwrap DEKs: reverse the XOR, then verify the HMAC tag.
    - Rotate CMKs: create a new version for a customer (old version kept until
      all records have been re-wrapped).
    - Delete CMKs for crypto-shredding (RTBF).
    """

    # Each CMK entry: {"cmk": bytes, "customer_id": str, "version": int}
    _store: dict[str, dict[str, object]]
    # customer_id -> list[cmk_id] ordered by version (oldest first)
    _customer_cmks: dict[str, list[str]]

    def __init__(self) -> None:
        self._store = {}
        self._customer_cmks = {}

    # ------------------------------------------------------------------
    # CMK management
    # ------------------------------------------------------------------

    def generate_cmk(self, customer_id: str) -> str:
        """Create a new CMK for *customer_id* and return its ``cmk_id``."""
        cmk_id = str(uuid.uuid4())
        cmk = secrets.token_bytes(32)
        version = len(self._customer_cmks.get(customer_id, [])) + 1
        self._store[cmk_id] = {
            "cmk": cmk,
            "customer_id": customer_id,
            "version": version,
        }
        self._customer_cmks.setdefault(customer_id, []).append(cmk_id)
        return cmk_id

    def rotate_cmk(self, customer_id: str) -> tuple[str, str]:
        """Create a new CMK version for *customer_id*.

        Returns ``(old_cmk_id, new_cmk_id)``.
        Raises :class:`KeyNotFoundError` if the customer has no existing CMK.
        """
        cmk_list = self._customer_cmks.get(customer_id)
        if not cmk_list:
            raise KeyNotFoundError(f"No CMK found for customer: {customer_id}")
        # Walk backwards to find the latest non-deleted key.
        old_cmk_id: str | None = None
        for cid in reversed(cmk_list):
            if cid in self._store:
                old_cmk_id = cid
                break
        if old_cmk_id is None:
            raise KeyNotFoundError(f"All CMKs for customer {customer_id} have been deleted.")
        new_cmk_id = self.generate_cmk(customer_id)
        return old_cmk_id, new_cmk_id

    def delete_cmk(self, cmk_id: str) -> None:
        """Permanently delete a CMK (crypto shredding).

        Raises :class:`KeyNotFoundError` if *cmk_id* does not exist.
        """
        if cmk_id not in self._store:
            raise KeyNotFoundError(f"CMK not found: {cmk_id}")
        del self._store[cmk_id]

    def get_active_cmk(self, customer_id: str) -> str:
        """Return the most-recent (active) CMK id for *customer_id*."""
        cmk_list = self._customer_cmks.get(customer_id)
        if not cmk_list:
            raise KeyNotFoundError(f"No CMK found for customer: {customer_id}")
        for cid in reversed(cmk_list):
            if cid in self._store:
                return cid
        raise KeyDeletedError(f"All CMKs for customer {customer_id} have been deleted.")

    def list_cmks(self, customer_id: str) -> list[str]:
        """Return all CMK ids (including deleted) for *customer_id*."""
        return list(self._customer_cmks.get(customer_id, []))

    # ------------------------------------------------------------------
    # DEK wrap / unwrap
    # ------------------------------------------------------------------

    def wrap_dek(self, cmk_id: str, dek: bytes) -> bytes:
        """Wrap (protect) *dek* under CMK *cmk_id*.

        Returns a 64-byte blob: ``tag (32 bytes) || (dek XOR tag)`` where
        ``tag = HMAC-SHA256(cmk, dek + b'\\x01')``.
        """
        cmk = self._get_cmk_bytes(cmk_id)
        tag = _hmac_sha256(cmk, dek + b"\x01")
        masked_dek = _xor_bytes(dek, tag)
        return tag + masked_dek

    def unwrap_dek(self, cmk_id: str, wrapped_dek: bytes) -> bytes:
        """Unwrap a DEK previously wrapped by :meth:`wrap_dek`.

        Raises :class:`AuthenticationError` if the MAC tag does not match
        (wrong key or corrupted blob).
        Raises :class:`KeyDeletedError` if the CMK has been deleted.
        """
        from colenc.cipher import AuthenticationError

        cmk = self._get_cmk_bytes(cmk_id)
        if len(wrapped_dek) != 64:
            raise ValueError(f"Wrapped DEK must be 64 bytes, got {len(wrapped_dek)}.")
        tag = wrapped_dek[:32]
        masked_dek = wrapped_dek[32:]
        dek = _xor_bytes(masked_dek, tag)
        expected_tag = _hmac_sha256(cmk, dek + b"\x01")
        if not hmac.compare_digest(tag, expected_tag):
            msg = "DEK unwrap failed: MAC mismatch (wrong key or corrupt blob)."
            raise AuthenticationError(msg)
        return dek

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_cmk_bytes(self, cmk_id: str) -> bytes:
        if cmk_id not in self._store:
            raise KeyDeletedError(f"CMK not found or has been deleted: {cmk_id}")
        return self._store[cmk_id]["cmk"]  # type: ignore[return-value]
