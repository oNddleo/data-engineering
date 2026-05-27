"""
HMAC-CTR stream cipher with Encrypt-then-MAC authentication.

Wire format produced by :meth:`HmacCtrCipher.encrypt`:
    nonce (16 bytes) || ciphertext (len(plaintext) bytes) || mac (32 bytes)

Security properties:
- Keystream is HMAC-SHA256(key, nonce || counter_as_8_bytes) per 32-byte block.
- MAC is HMAC-SHA256(key, nonce || ciphertext) — computed over ciphertext,
  not plaintext (Encrypt-then-MAC).  This prevents padding-oracle / chosen-
  ciphertext attacks and gives IND-CCA2 security.
- A fresh random nonce ensures keystream never repeats for the same key.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import struct


class AuthenticationError(Exception):
    """Raised when MAC verification fails during decryption."""


class HmacCtrCipher:
    """Authenticated stream cipher: HMAC-CTR + Encrypt-then-MAC."""

    BLOCK_SIZE: int = 32  # SHA-256 output — bytes per keystream block
    MAC_SIZE: int = 32  # HMAC-SHA256 output
    NONCE_SIZE: int = 16  # 128-bit nonce — collision probability negligible

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encrypt(self, key: bytes, plaintext: bytes) -> bytes:
        """Encrypt *plaintext* and return ``nonce || ciphertext || mac``."""
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        ciphertext = self._apply_keystream(key, nonce, plaintext)
        mac = self._compute_mac(key, nonce, ciphertext)
        return nonce + ciphertext + mac

    def decrypt(self, key: bytes, ciphertext_with_mac: bytes) -> bytes:
        """Decrypt *ciphertext_with_mac* and return the original plaintext.

        Raises :class:`AuthenticationError` if the MAC is invalid.
        """
        if len(ciphertext_with_mac) < self.NONCE_SIZE + self.MAC_SIZE:
            raise AuthenticationError("Ciphertext is too short to be valid.")

        nonce = ciphertext_with_mac[: self.NONCE_SIZE]
        mac = ciphertext_with_mac[-self.MAC_SIZE :]
        ciphertext = ciphertext_with_mac[self.NONCE_SIZE : -self.MAC_SIZE]

        expected_mac = self._compute_mac(key, nonce, ciphertext)
        if not hmac.compare_digest(mac, expected_mac):
            raise AuthenticationError("MAC verification failed — data is corrupt or key is wrong.")

        return self._apply_keystream(key, nonce, ciphertext)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _keystream_block(self, key: bytes, nonce: bytes, counter: int) -> bytes:
        """Return one BLOCK_SIZE keystream block for *counter*."""
        counter_bytes = struct.pack(">Q", counter)  # big-endian uint64
        return hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest()

    def _apply_keystream(self, key: bytes, nonce: bytes, data: bytes) -> bytes:
        """XOR *data* with the HMAC-CTR keystream derived from *key* and *nonce*."""
        output = bytearray(len(data))
        offset = 0
        counter = 0
        while offset < len(data):
            block = self._keystream_block(key, nonce, counter)
            chunk = data[offset : offset + self.BLOCK_SIZE]
            for i, byte in enumerate(chunk):
                output[offset + i] = byte ^ block[i]
            offset += self.BLOCK_SIZE
            counter += 1
        return bytes(output)

    def _compute_mac(self, key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
        """Return HMAC-SHA256(key, nonce || ciphertext)."""
        return hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
