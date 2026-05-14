"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ekycpipe.cccd import build_cccd, parse_cccd
from ekycpipe.crypto import HmacStreamCipher
from ekycpipe.encryption import (
    SENSITIVE_COLUMNS,
    KeyManager,
    decrypt_record,
    encrypt_record,
)
from ekycpipe.provinces import PROVINCE_CODES
from ekycpipe.schema import Gender

from ._fixtures import make_citizen

# Subset of currencies/provinces tied to canonical fixture-supported values.
_PROVINCE = st.sampled_from(list(PROVINCE_CODES.keys()))
_BIRTH_YEAR = st.integers(min_value=1900, max_value=2299)
_GENDER = st.sampled_from(list(Gender))
_SERIAL = st.text(alphabet="0123456789", min_size=6, max_size=6)


@given(province=_PROVINCE, year=_BIRTH_YEAR, gender=_GENDER, serial=_SERIAL)
def test_build_parse_round_trip(province, year, gender, serial):
    """Property: build_cccd → parse_cccd recovers the same fields."""
    cccd = build_cccd(province_code=province, gender=gender, birth_year=year, serial=serial)
    f = parse_cccd(cccd)
    assert f.province_code == province
    assert f.gender is gender
    assert f.birth_year == year
    assert f.serial == serial


@given(plaintext=st.binary(min_size=0, max_size=200))
def test_cipher_round_trip(plaintext):
    """Property: AEAD round-trips any byte string up to 200 bytes."""
    c = HmacStreamCipher(b"\x42" * 32)
    assert c.decrypt(c.encrypt(plaintext)) == plaintext


@given(
    full_name=st.text(
        min_size=1,
        max_size=50,
        # ASCII letters + space — covers UTF-8 round-trip without hitting
        # CitizenRecord's "non-blank name" invariant on whitespace-only strings.
        alphabet=st.characters(min_codepoint=65, max_codepoint=122),
    ).filter(lambda s: s.strip() != "")
)
def test_encrypt_record_round_trip(full_name):
    """Property: encrypt → decrypt recovers the same citizen for any non-blank name."""
    km = KeyManager({"K-PII": b"\x99" * 32})
    policy = {c: "K-PII" for c in SENSITIVE_COLUMNS}
    record = make_citizen(full_name=full_name)
    enc = encrypt_record(record, km, policy)
    decrypted = decrypt_record(enc, km, policy)
    assert decrypted == record


@given(plaintext=st.binary(min_size=0, max_size=100))
def test_cipher_two_encryptions_differ(plaintext):
    """Property: random nonce → repeated encrypt() must produce distinct blobs (except for empty plaintext, where
    the body is empty and only the nonce + tag differ)."""
    c = HmacStreamCipher(b"\x42" * 32)
    a = c.encrypt(plaintext)
    b = c.encrypt(plaintext)
    # Even with empty plaintext, the nonce is fresh per call so the blobs must differ.
    assert a != b
