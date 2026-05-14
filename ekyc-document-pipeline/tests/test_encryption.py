"""Column-level encryption tests."""

from __future__ import annotations

from datetime import date

import pytest

from ekycpipe.encryption import (
    SENSITIVE_COLUMNS,
    KeyManager,
    cccd_index_hash,
    decrypt_record,
    encrypt_record,
)

from ._fixtures import make_citizen


def _two_keys() -> KeyManager:
    return KeyManager({"K-PII": b"\x01" * 32, "K-DOB": b"\x02" * 32})


def _all_pii_policy(key_id: str) -> dict[str, str]:
    return {c: key_id for c in SENSITIVE_COLUMNS}


def test_key_manager_lookup():
    km = _two_keys()
    assert "K-PII" in km.key_ids
    assert km.cipher_for("K-PII") is not None


def test_key_manager_rejects_wrong_size_key():
    with pytest.raises(ValueError):
        KeyManager({"BAD": b"too short"})


def test_key_manager_rejects_unknown_id():
    with pytest.raises(KeyError):
        _two_keys().cipher_for("K-MISSING")


def test_cccd_index_hash_is_hex():
    h = cccd_index_hash("079095012345")
    assert len(h) == 64
    int(h, 16)  # parses as hex


def test_cccd_index_hash_deterministic():
    assert cccd_index_hash("079095012345") == cccd_index_hash("079095012345")
    assert cccd_index_hash("079095012345") != cccd_index_hash("001302654321")


def test_encrypt_decrypt_round_trip_single_key():
    km = _two_keys()
    policy = _all_pii_policy("K-PII")
    r = make_citizen()
    enc = encrypt_record(r, km, policy)
    decrypted = decrypt_record(enc, km, policy)
    assert decrypted == r


def test_encrypt_decrypt_round_trip_per_column_keys():
    km = _two_keys()
    policy = {col: "K-PII" for col in SENSITIVE_COLUMNS}
    policy["date_of_birth"] = "K-DOB"
    r = make_citizen()
    enc = encrypt_record(r, km, policy)
    decrypted = decrypt_record(enc, km, policy)
    assert decrypted == r


def test_encrypt_preserves_index_hash_for_lookup():
    km = _two_keys()
    policy = _all_pii_policy("K-PII")
    r = make_citizen()
    enc = encrypt_record(r, km, policy)
    assert enc.cccd_index_hash == cccd_index_hash(r.cccd)


def test_encrypt_does_not_expose_plaintext():
    """No plaintext field of any PII should appear in any ciphertext blob."""
    km = _two_keys()
    policy = _all_pii_policy("K-PII")
    r = make_citizen(full_name="Nguyễn Văn ABCXYZ-UNIQUE")
    enc = encrypt_record(r, km, policy)
    pt_marker = b"ABCXYZ-UNIQUE"
    blobs = (
        enc.cccd_ciphertext,
        enc.full_name_ciphertext,
        enc.date_of_birth_ciphertext,
        enc.place_of_residence_ciphertext,
    )
    for blob in blobs:
        assert pt_marker not in blob


def test_encrypt_handles_none_expires_at():
    km = _two_keys()
    policy = _all_pii_policy("K-PII")
    r = make_citizen(expires_at=None)
    enc = encrypt_record(r, km, policy)
    decrypted = decrypt_record(enc, km, policy)
    assert decrypted.expires_at is None


def test_encrypt_handles_real_expires_at():
    km = _two_keys()
    policy = _all_pii_policy("K-PII")
    r = make_citizen(expires_at=date(2033, 1, 15))
    enc = encrypt_record(r, km, policy)
    decrypted = decrypt_record(enc, km, policy)
    assert decrypted.expires_at == date(2033, 1, 15)


def test_two_encryptions_produce_different_ciphertexts():
    """Random nonce per encryption → different blobs even for same record."""
    km = _two_keys()
    policy = _all_pii_policy("K-PII")
    r = make_citizen()
    enc1 = encrypt_record(r, km, policy)
    enc2 = encrypt_record(r, km, policy)
    assert enc1.full_name_ciphertext != enc2.full_name_ciphertext
    # But the index hash is the same — that's how lookups work.
    assert enc1.cccd_index_hash == enc2.cccd_index_hash


def test_encrypt_rejects_missing_policy_column():
    km = _two_keys()
    bad_policy = {c: "K-PII" for c in SENSITIVE_COLUMNS if c != "full_name"}
    r = make_citizen()
    with pytest.raises(ValueError):
        encrypt_record(r, km, bad_policy)


def test_encrypt_rejects_unknown_key_id_in_policy():
    km = _two_keys()
    policy = _all_pii_policy("K-MISSING")
    r = make_citizen()
    with pytest.raises(KeyError):
        encrypt_record(r, km, policy)


def test_decrypt_with_wrong_key_for_column_fails():
    km = _two_keys()
    enc_policy = _all_pii_policy("K-PII")
    dec_policy = _all_pii_policy("K-DOB")
    r = make_citizen()
    enc = encrypt_record(r, km, enc_policy)
    from ekycpipe.crypto import IntegrityError

    with pytest.raises(IntegrityError):
        decrypt_record(enc, km, dec_policy)
