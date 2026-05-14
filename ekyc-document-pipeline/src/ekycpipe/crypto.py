"""HMAC-based authenticated stream cipher — educational AEAD on stdlib only.

The goal of this project is to demonstrate **column-level encryption
of PII**, not to reinvent AES. So we build a small authenticated
encryption primitive out of ``hmac`` + ``hashlib`` + ``secrets``,
all in the standard library:

* **Key** — 32 bytes (caller-supplied via :class:`KeyManager`).
* **Encrypt(plaintext)**:

  1. Generate a 12-byte random nonce with :func:`secrets.token_bytes`.
  2. Derive a keystream of ``len(plaintext)`` bytes from
     ``HMAC-SHA256(key, nonce || counter)`` for ``counter = 0, 1, 2, …``.
  3. XOR the keystream into the plaintext to produce the ciphertext.
  4. Compute a 16-byte authentication tag as
     ``HMAC-SHA256(key, b"AUTH" || nonce || ciphertext)[:16]``.
  5. Output ``nonce || ciphertext || tag``.

* **Decrypt(blob)** — parses out the three sections, recomputes the
  tag, constant-time compares, and only then XORs the keystream
  back out. A tampered nonce, ciphertext, or tag fails with
  :class:`IntegrityError`.

**This is for learning.** It's structurally similar to a stream
AEAD (encrypt-then-MAC), uses the same primitive twice (so a key
compromise leaks both encryption and authentication keys), and the
counter mode is constructed by hand. Production systems should use
``cryptography.fernet.Fernet`` or AES-GCM from a vetted library.
We say so loudly in the README.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Protocol


class IntegrityError(Exception):
    """Raised when a ciphertext fails MAC verification."""


class Cipher(Protocol):
    """Anything with an encrypt/decrypt pair satisfies this."""

    def encrypt(self, plaintext: bytes) -> bytes: ...
    def decrypt(self, ciphertext: bytes) -> bytes: ...


class HmacStreamCipher:
    """HMAC-SHA256 keystream + Encrypt-then-MAC AEAD construction.

    Uses 32-byte keys, 12-byte nonces, 16-byte truncated tags.
    """

    KEY_SIZE = 32
    NONCE_SIZE = 12
    TAG_SIZE = 16
    _AUTH_PREFIX = b"AUTH"

    def __init__(self, key: bytes) -> None:
        if len(key) != self.KEY_SIZE:
            raise ValueError(f"key must be {self.KEY_SIZE} bytes, got {len(key)}")
        self._key = key

    def _keystream(self, nonce: bytes, length: int) -> bytes:
        """Generate ``length`` keystream bytes from ``nonce``.

        Each 32-byte block is ``HMAC-SHA256(key, nonce || counter_be_4)``
        with the counter starting at 0.
        """
        out = bytearray()
        counter = 0
        while len(out) < length:
            block = hmac.new(self._key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
            out.extend(block)
            counter += 1
        return bytes(out[:length])

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        return self._encrypt_with_nonce(plaintext, nonce)

    def _encrypt_with_nonce(self, plaintext: bytes, nonce: bytes) -> bytes:
        """Test-only entry point that lets us inject a deterministic nonce."""
        ks = self._keystream(nonce, len(plaintext))
        ciphertext = bytes(p ^ k for p, k in zip(plaintext, ks, strict=True))
        tag = hmac.new(self._key, self._AUTH_PREFIX + nonce + ciphertext, hashlib.sha256).digest()[
            : self.TAG_SIZE
        ]
        return nonce + ciphertext + tag

    def decrypt(self, blob: bytes) -> bytes:
        if len(blob) < self.NONCE_SIZE + self.TAG_SIZE:
            raise IntegrityError(
                f"blob too short to be valid ciphertext (need >= "
                f"{self.NONCE_SIZE + self.TAG_SIZE} bytes, got {len(blob)})"
            )
        nonce = blob[: self.NONCE_SIZE]
        tag_offset = len(blob) - self.TAG_SIZE
        ciphertext = blob[self.NONCE_SIZE : tag_offset]
        tag = blob[tag_offset:]
        expected = hmac.new(
            self._key, self._AUTH_PREFIX + nonce + ciphertext, hashlib.sha256
        ).digest()[: self.TAG_SIZE]
        if not hmac.compare_digest(tag, expected):
            raise IntegrityError("invalid authentication tag")
        ks = self._keystream(nonce, len(ciphertext))
        return bytes(c ^ k for c, k in zip(ciphertext, ks, strict=True))


def derive_key(passphrase: str, salt: bytes, *, iterations: int = 200_000) -> bytes:
    """Derive a 32-byte key from a passphrase using PBKDF2-HMAC-SHA256.

    For demo / test setup only — production key material should come
    from a KMS (AWS KMS, GCP KMS, HashiCorp Vault), not a passphrase.
    """
    if not salt:
        raise ValueError("salt must be non-empty")
    return hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode("utf-8"), salt, iterations, dklen=HmacStreamCipher.KEY_SIZE
    )


__all__ = ["Cipher", "HmacStreamCipher", "IntegrityError", "derive_key"]
