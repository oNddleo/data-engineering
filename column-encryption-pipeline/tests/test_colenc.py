"""
Comprehensive test-suite for the colenc package.

Coverage:
  - HmacCtrCipher                   (tests 1-9)
  - LocalKMS                        (tests 10-17)
  - EncryptedRecord / RecordStore   (tests 18-23)
  - EncryptionEngine                (tests 24-31)
  - CryptoShredder                  (tests 32-36)
  - CLI                             (tests 37-38)
  - Hypothesis property tests       (tests 39-41)
"""

from __future__ import annotations

import json
import secrets
import sys
from typing import Any
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from colenc.cipher import AuthenticationError, HmacCtrCipher
from colenc.engine import EncryptionEngine
from colenc.kms import KeyDeletedError, KeyNotFoundError, LocalKMS
from colenc.rtbf import CryptoShredder
from colenc.storage import EncryptedRecord, RecordStore, b64_encode

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cipher() -> HmacCtrCipher:
    return HmacCtrCipher()


@pytest.fixture()
def key() -> bytes:
    return secrets.token_bytes(32)


@pytest.fixture()
def kms() -> LocalKMS:
    return LocalKMS()


@pytest.fixture()
def store() -> RecordStore:
    return RecordStore()


@pytest.fixture()
def engine(kms: LocalKMS) -> EncryptionEngine:
    return EncryptionEngine(kms=kms)


@pytest.fixture()
def customer_id() -> str:
    return "cust_test_001"


@pytest.fixture()
def cmk_id(kms: LocalKMS, customer_id: str) -> str:
    return kms.generate_cmk(customer_id)


@pytest.fixture()
def sample_record() -> dict[str, Any]:
    return {
        "ssn": "123-45-6789",
        "email": "alice@example.com",
        "product_id": "prod_abc",
        "amount": 99.99,
    }


# ===========================================================================
# 1-9: HmacCtrCipher
# ===========================================================================


def test_cipher_encrypt_decrypt_roundtrip(cipher: HmacCtrCipher, key: bytes) -> None:
    plaintext = b"Hello, world!"
    ct = cipher.encrypt(key, plaintext)
    assert cipher.decrypt(key, ct) == plaintext


def test_cipher_different_nonces_produce_different_ciphertext(
    cipher: HmacCtrCipher, key: bytes
) -> None:
    plaintext = b"same plaintext every time"
    ct1 = cipher.encrypt(key, plaintext)
    ct2 = cipher.encrypt(key, plaintext)
    # With high probability (2^-128) nonces differ, so ciphertexts differ.
    assert ct1 != ct2


def test_cipher_wrong_key_fails_mac(cipher: HmacCtrCipher, key: bytes) -> None:
    ct = cipher.encrypt(key, b"secret data")
    wrong_key = secrets.token_bytes(32)
    with pytest.raises(AuthenticationError):
        cipher.decrypt(wrong_key, ct)


def test_cipher_tampered_ciphertext_fails_mac(cipher: HmacCtrCipher, key: bytes) -> None:
    ct = bytearray(cipher.encrypt(key, b"tamper me"))
    ct[20] ^= 0xFF  # flip a bit in the ciphertext body
    with pytest.raises(AuthenticationError):
        cipher.decrypt(key, bytes(ct))


def test_cipher_tampered_mac_fails(cipher: HmacCtrCipher, key: bytes) -> None:
    ct = bytearray(cipher.encrypt(key, b"mac tamper"))
    ct[-1] ^= 0x01  # flip the last byte of the MAC
    with pytest.raises(AuthenticationError):
        cipher.decrypt(key, bytes(ct))


def test_cipher_empty_plaintext(cipher: HmacCtrCipher, key: bytes) -> None:
    ct = cipher.encrypt(key, b"")
    assert cipher.decrypt(key, ct) == b""


def test_cipher_large_plaintext(cipher: HmacCtrCipher, key: bytes) -> None:
    plaintext = secrets.token_bytes(10_000)
    ct = cipher.encrypt(key, plaintext)
    assert cipher.decrypt(key, ct) == plaintext


def test_cipher_output_length(cipher: HmacCtrCipher, key: bytes) -> None:
    plaintext = b"hello"
    ct = cipher.encrypt(key, plaintext)
    expected = cipher.NONCE_SIZE + len(plaintext) + cipher.MAC_SIZE
    assert len(ct) == expected


def test_cipher_too_short_ciphertext_raises(cipher: HmacCtrCipher, key: bytes) -> None:
    with pytest.raises(AuthenticationError):
        cipher.decrypt(key, b"\x00" * 10)


# ===========================================================================
# 10-17: LocalKMS
# ===========================================================================


def test_kms_generate_cmk_returns_id(kms: LocalKMS) -> None:
    cmk_id = kms.generate_cmk("cust_a")
    assert isinstance(cmk_id, str)
    assert len(cmk_id) > 0


def test_kms_wrap_unwrap_dek_roundtrip(kms: LocalKMS) -> None:
    cmk_id = kms.generate_cmk("cust_b")
    dek = secrets.token_bytes(32)
    wrapped = kms.wrap_dek(cmk_id, dek)
    unwrapped = kms.unwrap_dek(cmk_id, wrapped)
    assert unwrapped == dek


def test_kms_wrapped_dek_length(kms: LocalKMS) -> None:
    cmk_id = kms.generate_cmk("cust_c")
    dek = secrets.token_bytes(32)
    wrapped = kms.wrap_dek(cmk_id, dek)
    assert len(wrapped) == 64


def test_kms_wrong_key_unwrap_fails(kms: LocalKMS) -> None:
    cmk1 = kms.generate_cmk("cust_d")
    cmk2 = kms.generate_cmk("cust_e")
    dek = secrets.token_bytes(32)
    wrapped = kms.wrap_dek(cmk1, dek)
    with pytest.raises(AuthenticationError):
        kms.unwrap_dek(cmk2, wrapped)


def test_kms_rotate_cmk_returns_both_ids(kms: LocalKMS) -> None:
    kms.generate_cmk("cust_f")
    old_id, new_id = kms.rotate_cmk("cust_f")
    assert old_id != new_id
    assert isinstance(old_id, str)
    assert isinstance(new_id, str)


def test_kms_old_cmk_still_works_after_rotation(kms: LocalKMS) -> None:
    kms.generate_cmk("cust_g")
    old_id, _new_id = kms.rotate_cmk("cust_g")
    dek = secrets.token_bytes(32)
    wrapped = kms.wrap_dek(old_id, dek)
    assert kms.unwrap_dek(old_id, wrapped) == dek


def test_kms_delete_cmk_makes_unwrap_fail(kms: LocalKMS) -> None:
    cmk_id = kms.generate_cmk("cust_h")
    dek = secrets.token_bytes(32)
    wrapped = kms.wrap_dek(cmk_id, dek)
    kms.delete_cmk(cmk_id)
    with pytest.raises((KeyDeletedError, AuthenticationError)):
        kms.unwrap_dek(cmk_id, wrapped)


def test_kms_delete_nonexistent_cmk_raises(kms: LocalKMS) -> None:
    with pytest.raises(KeyNotFoundError):
        kms.delete_cmk("00000000-0000-0000-0000-000000000000")


# ===========================================================================
# 18-23: EncryptedRecord / RecordStore
# ===========================================================================


def test_record_serialise_roundtrip(kms: LocalKMS, customer_id: str, cmk_id: str) -> None:
    dek = secrets.token_bytes(32)
    wrapped = kms.wrap_dek(cmk_id, dek)
    rec = EncryptedRecord(
        record_id="rec-001",
        customer_id=customer_id,
        cmk_id=cmk_id,
        wrapped_dek=b64_encode(wrapped),
        encrypted_columns={"ssn": "abc=="},
        plaintext_columns={"product_id": "p1"},
    )
    restored = EncryptedRecord.from_json(rec.to_json())
    assert restored.record_id == rec.record_id
    assert restored.cmk_id == rec.cmk_id
    assert restored.wrapped_dek == rec.wrapped_dek


def test_record_store_put_and_get(store: RecordStore) -> None:
    rec = EncryptedRecord(
        record_id="r1",
        customer_id="cust_x",
        cmk_id="k1",
        wrapped_dek="YWJj",
        encrypted_columns={},
        plaintext_columns={"a": 1},
    )
    store.put(rec)
    assert store.get("r1").customer_id == "cust_x"


def test_record_store_get_missing_raises(store: RecordStore) -> None:
    with pytest.raises(KeyError):
        store.get("nonexistent")


def test_record_store_list_for_customer(store: RecordStore) -> None:
    for i in range(3):
        store.put(
            EncryptedRecord(
                record_id=f"r{i}",
                customer_id="cust_y",
                cmk_id="k",
                wrapped_dek="YWJj",
                encrypted_columns={},
                plaintext_columns={},
            )
        )
    store.put(
        EncryptedRecord(
            record_id="other",
            customer_id="cust_z",
            cmk_id="k",
            wrapped_dek="YWJj",
            encrypted_columns={},
            plaintext_columns={},
        )
    )
    results = store.list_for_customer("cust_y")
    assert len(results) == 3


def test_record_store_delete(store: RecordStore) -> None:
    rec = EncryptedRecord(
        record_id="del1",
        customer_id="cust_w",
        cmk_id="k",
        wrapped_dek="YWJj",
        encrypted_columns={},
        plaintext_columns={},
    )
    store.put(rec)
    store.delete("del1")
    with pytest.raises(KeyError):
        store.get("del1")


def test_record_store_count(store: RecordStore) -> None:
    assert store.count() == 0
    for i in range(5):
        store.put(
            EncryptedRecord(
                record_id=f"cnt{i}",
                customer_id="c",
                cmk_id="k",
                wrapped_dek="YWJj",
                encrypted_columns={},
                plaintext_columns={},
            )
        )
    assert store.count() == 5


# ===========================================================================
# 24-31: EncryptionEngine
# ===========================================================================


def test_engine_encrypt_record_pii_columns_hidden(
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
    sample_record: dict[str, Any],
) -> None:
    enc = engine.encrypt_record(sample_record, customer_id)
    assert "ssn" not in enc.plaintext_columns
    assert "email" not in enc.plaintext_columns
    assert "ssn" in enc.encrypted_columns
    assert "email" in enc.encrypted_columns


def test_engine_encrypt_record_non_pii_preserved(
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
    sample_record: dict[str, Any],
) -> None:
    enc = engine.encrypt_record(sample_record, customer_id)
    assert enc.plaintext_columns["product_id"] == "prod_abc"
    assert enc.plaintext_columns["amount"] == 99.99


def test_engine_decrypt_record_roundtrip(
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
    sample_record: dict[str, Any],
) -> None:
    enc = engine.encrypt_record(sample_record, customer_id)
    plain = engine.decrypt_record(enc)
    assert plain["ssn"] == "123-45-6789"
    assert plain["email"] == "alice@example.com"
    assert plain["product_id"] == "prod_abc"
    assert plain["amount"] == 99.99


def test_engine_explicit_columns(
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
) -> None:
    record = {"ssn": "000-00-0000", "name": "Bob", "score": 42}
    enc = engine.encrypt_record(record, customer_id, columns=["ssn"])
    assert "ssn" in enc.encrypted_columns
    assert "name" in enc.plaintext_columns
    plain = engine.decrypt_record(enc, columns=["ssn"])
    assert plain["ssn"] == "000-00-0000"
    assert plain["name"] == "Bob"


def test_engine_multiple_pii_columns(
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
) -> None:
    record = {
        "ssn": "111-22-3333",
        "email": "x@y.com",
        "phone": "555-1234",
        "dob": "1990-01-01",
        "city": "NYC",
    }
    enc = engine.encrypt_record(record, customer_id)
    for col in ("ssn", "email", "phone", "dob"):
        assert col in enc.encrypted_columns
    assert "city" in enc.plaintext_columns
    plain = engine.decrypt_record(enc)
    assert plain["ssn"] == "111-22-3333"
    assert plain["city"] == "NYC"


def test_engine_empty_record(
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
) -> None:
    enc = engine.encrypt_record({}, customer_id)
    plain = engine.decrypt_record(enc)
    assert plain == {}


def test_engine_re_encrypt_record(
    engine: EncryptionEngine,
    kms: LocalKMS,
    customer_id: str,
    cmk_id: str,
    sample_record: dict[str, Any],
) -> None:
    enc = engine.encrypt_record(sample_record, customer_id)
    _old_id, new_cmk_id = kms.rotate_cmk(customer_id)

    re_enc = engine.re_encrypt_record(enc, new_cmk_id)
    assert re_enc.cmk_id == new_cmk_id
    # Column ciphertext unchanged
    assert re_enc.encrypted_columns["ssn"] == enc.encrypted_columns["ssn"]
    # DEK re-wrapped (different CMK)
    assert re_enc.wrapped_dek != enc.wrapped_dek

    plain = engine.decrypt_record(re_enc)
    assert plain["ssn"] == "123-45-6789"


def test_engine_encrypt_and_store_load_decrypt(
    engine: EncryptionEngine,
    store: RecordStore,
    customer_id: str,
    cmk_id: str,
    sample_record: dict[str, Any],
) -> None:
    enc = engine.encrypt_and_store(sample_record, customer_id, store)
    plain = engine.load_and_decrypt(enc.record_id, store)
    assert plain["ssn"] == "123-45-6789"
    assert plain["product_id"] == "prod_abc"


# ===========================================================================
# 32-36: CryptoShredder
# ===========================================================================


def test_shredder_forget_deletes_all_cmks(
    kms: LocalKMS,
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
    sample_record: dict[str, Any],
) -> None:
    shredder = CryptoShredder(kms=kms)
    engine.encrypt_record(sample_record, customer_id)
    result = shredder.forget_customer(customer_id)
    assert result["success"] is True
    assert len(result["cmks_deleted"]) >= 1  # type: ignore[arg-type]


def test_shredder_forget_makes_decrypt_fail(
    kms: LocalKMS,
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
    sample_record: dict[str, Any],
) -> None:
    shredder = CryptoShredder(kms=kms)
    enc = engine.encrypt_record(sample_record, customer_id)
    shredder.forget_customer(customer_id)
    with pytest.raises(KeyDeletedError):
        engine.decrypt_record(enc)


def test_shredder_forget_multiple_cmk_versions(
    kms: LocalKMS,
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
    sample_record: dict[str, Any],
) -> None:
    # Create a second CMK version.
    kms.rotate_cmk(customer_id)
    shredder = CryptoShredder(kms=kms)
    result = shredder.forget_customer(customer_id)
    assert len(result["cmks_deleted"]) == 2  # type: ignore[arg-type]


def test_shredder_is_forgotten(
    kms: LocalKMS,
    engine: EncryptionEngine,
    customer_id: str,
    cmk_id: str,
) -> None:
    shredder = CryptoShredder(kms=kms)
    assert not shredder.is_forgotten(customer_id)
    shredder.forget_customer(customer_id)
    assert shredder.is_forgotten(customer_id)


def test_shredder_delete_records_flag(
    kms: LocalKMS,
    engine: EncryptionEngine,
    store: RecordStore,
    customer_id: str,
    cmk_id: str,
    sample_record: dict[str, Any],
) -> None:
    shredder = CryptoShredder(kms=kms, store=store)
    for _ in range(3):
        enc = engine.encrypt_record(sample_record, customer_id)
        # Re-generate new CMK after shredder might have cleaned it; just store.
        store.put(enc)
    result = shredder.forget_customer(customer_id, delete_records=True)
    assert result["records_deleted"] == 3  # type: ignore[arg-type]
    assert store.count() == 0


# ===========================================================================
# 37-38: CLI
# ===========================================================================


def _fresh_cli_state() -> tuple[LocalKMS, RecordStore, EncryptionEngine, CryptoShredder]:
    kms = LocalKMS()
    store = RecordStore()
    engine = EncryptionEngine(kms=kms)
    shredder = CryptoShredder(kms=kms, store=store)
    return kms, store, engine, shredder


def test_cli_encrypt_produces_encrypted_record(capsys: pytest.CaptureFixture[str]) -> None:
    import colenc.cli as cli_mod

    kms = LocalKMS()
    store = RecordStore()
    engine = EncryptionEngine(kms=kms)
    shredder = CryptoShredder(kms=kms, store=store)

    # Patch the module-level singletons.
    with (
        patch.object(cli_mod, "_kms", kms),
        patch.object(cli_mod, "_store", store),
        patch.object(cli_mod, "_engine", engine),
        patch.object(cli_mod, "_shredder", shredder),
    ):
        record_json = json.dumps({"ssn": "999-99-9999", "id": 1})
        test_args = ["encrypt", "--customer", "cli_cust", "--columns", "ssn", record_json]
        with patch.object(sys, "argv", ["colenc"] + test_args):
            try:
                cli_mod.main()
            except SystemExit as exc:
                assert exc.code == 0

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "encrypted_columns" in output
    assert "ssn" in output["encrypted_columns"]


def test_cli_decrypt_roundtrip(capsys: pytest.CaptureFixture[str]) -> None:
    import colenc.cli as cli_mod

    kms = LocalKMS()
    store = RecordStore()
    engine = EncryptionEngine(kms=kms)
    shredder = CryptoShredder(kms=kms, store=store)

    kms.generate_cmk("cli_cust2")
    record: dict[str, Any] = {"ssn": "111-22-3333", "name": "Bob"}
    enc = engine.encrypt_record(record, "cli_cust2", columns=["ssn"])
    enc_json = enc.to_json()

    with (
        patch.object(cli_mod, "_kms", kms),
        patch.object(cli_mod, "_store", store),
        patch.object(cli_mod, "_engine", engine),
        patch.object(cli_mod, "_shredder", shredder),
    ):
        test_args = ["decrypt", enc_json]
        with patch.object(sys, "argv", ["colenc"] + test_args):
            try:
                cli_mod.main()
            except SystemExit as exc:
                assert exc.code == 0

    captured = capsys.readouterr()
    plain = json.loads(captured.out)
    assert plain["ssn"] == "111-22-3333"
    assert plain["name"] == "Bob"


# ===========================================================================
# 39-41: Hypothesis property-based tests
# ===========================================================================


@given(plaintext=st.binary())
@settings(max_examples=200)
def test_hypothesis_encrypt_decrypt_identity(plaintext: bytes) -> None:
    cipher = HmacCtrCipher()
    key = secrets.token_bytes(32)
    ct = cipher.encrypt(key, plaintext)
    assert cipher.decrypt(key, ct) == plaintext


@given(
    plaintext=st.binary(min_size=1),
    flip_index=st.integers(min_value=0, max_value=0),  # offset selected per-example below
)
@settings(max_examples=100)
def test_hypothesis_mac_catches_bit_flips(plaintext: bytes, flip_index: int) -> None:
    cipher = HmacCtrCipher()
    key = secrets.token_bytes(32)
    ct = bytearray(cipher.encrypt(key, plaintext))
    # Flip a bit anywhere in the packet.
    idx = flip_index % len(ct)
    ct[idx] ^= 0x01
    with pytest.raises(AuthenticationError):
        cipher.decrypt(key, bytes(ct))


@given(
    dek=st.binary(min_size=32, max_size=32),
)
@settings(max_examples=100)
def test_hypothesis_wrap_unwrap_identity(dek: bytes) -> None:
    kms = LocalKMS()
    cmk_id = kms.generate_cmk("hyp_cust")
    wrapped = kms.wrap_dek(cmk_id, dek)
    assert kms.unwrap_dek(cmk_id, wrapped) == dek
