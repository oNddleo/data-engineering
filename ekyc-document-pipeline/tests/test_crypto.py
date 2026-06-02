"""HmacStreamCipher AEAD tests."""

from __future__ import annotations

import pytest

from ekycpipe.crypto import HmacStreamCipher, IntegrityError, derive_key


def _key() -> bytes:
    return b"\x00" * 32


def test_round_trip_short_plaintext():
    c = HmacStreamCipher(_key())
    pt = b"hello"
    assert c.decrypt(c.encrypt(pt)) == pt


def test_round_trip_long_plaintext():
    c = HmacStreamCipher(_key())
    pt = b"A" * 1000
    assert c.decrypt(c.encrypt(pt)) == pt


def test_round_trip_empty_plaintext():
    c = HmacStreamCipher(_key())
    assert c.decrypt(c.encrypt(b"")) == b""


def test_round_trip_unicode_bytes():
    c = HmacStreamCipher(_key())
    pt = "Nguyễn Văn Á — TP. HCM".encode()
    assert c.decrypt(c.encrypt(pt)) == pt


def test_two_encryptions_have_different_ciphertext_due_to_random_nonce():
    c = HmacStreamCipher(_key())
    a = c.encrypt(b"same plaintext")
    b = c.encrypt(b"same plaintext")
    assert a != b


def test_decrypt_with_wrong_key_fails():
    c1 = HmacStreamCipher(b"\x00" * 32)
    c2 = HmacStreamCipher(b"\x01" * 32)
    blob = c1.encrypt(b"hello")
    with pytest.raises(IntegrityError):
        c2.decrypt(blob)


def test_decrypt_rejects_tampered_ciphertext():
    c = HmacStreamCipher(_key())
    blob = c.encrypt(b"hello")
    # Flip a single byte of the ciphertext body (after nonce, before tag).
    tampered = bytearray(blob)
    tampered[12 + 1] ^= 0xFF
    with pytest.raises(IntegrityError):
        c.decrypt(bytes(tampered))


def test_decrypt_rejects_tampered_tag():
    c = HmacStreamCipher(_key())
    blob = c.encrypt(b"hello")
    tampered = bytearray(blob)
    tampered[-1] ^= 0xFF
    with pytest.raises(IntegrityError):
        c.decrypt(bytes(tampered))


def test_decrypt_rejects_truncated_blob():
    c = HmacStreamCipher(_key())
    blob = c.encrypt(b"hello")
    with pytest.raises(IntegrityError):
        c.decrypt(blob[:10])


def test_key_size_enforced():
    with pytest.raises(ValueError):
        HmacStreamCipher(b"\x00" * 16)
    with pytest.raises(ValueError):
        HmacStreamCipher(b"\x00" * 64)


def test_derive_key_is_deterministic():
    a = derive_key("password", b"salt-bytes")
    b = derive_key("password", b"salt-bytes")
    assert a == b
    assert len(a) == 32


def test_derive_key_changes_with_salt():
    a = derive_key("password", b"salt-1")
    b = derive_key("password", b"salt-2")
    assert a != b


def test_derive_key_rejects_empty_salt():
    with pytest.raises(ValueError):
        derive_key("password", b"")


def test_deterministic_encrypt_with_fixed_nonce():
    """Internal helper: same nonce + plaintext → same ciphertext (for testing only)."""
    c = HmacStreamCipher(_key())
    nonce = b"\x00" * 12
    a = c._encrypt_with_nonce(b"hello", nonce)
    b = c._encrypt_with_nonce(b"hello", nonce)
    assert a == b
