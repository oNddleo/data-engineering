"""Column-level encryption for citizen records.

The motivating concept from Nghị định 13/2023/NĐ-CP (personal-data
protection) is that not every team should see every field. A
column-level scheme assigns each PII column to a *key id*. The
``KeyManager`` knows which raw key bytes to use for which id;
analysts only get the key ids they're entitled to.

So in this module we model:

* :class:`KeyManager` — wraps ``{key_id: 32-byte-key}``. Lookup
  returns a :class:`Cipher`.
* ``policies`` — ``{column: key_id}`` mapping. Different deployments
  can assign different columns to different keys.
* :class:`EncryptedCitizenRecord` — every PII field stored as raw
  AEAD ciphertext bytes. Plus a non-PII ``cccd_index_hash`` for
  index lookups without decryption.

The :func:`encrypt_record` / :func:`decrypt_record` round-trip is
deterministic over inputs *except* for the random nonce inside each
ciphertext. That means a fresh encryption of the same input
produces a different blob — which is the point.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

from ekycpipe.crypto import HmacStreamCipher
from ekycpipe.schema import CitizenRecord, Gender

SENSITIVE_COLUMNS: tuple[str, ...] = (
    "cccd",
    "full_name",
    "date_of_birth",
    "gender",
    "hometown_province_code",
    "place_of_residence",
    "issued_at",
    "expires_at",
)
"""Every PII column the encryption layer recognises."""


class KeyManager:
    """A simple in-memory registry of key_id → key bytes.

    Production deployments swap this for a KMS-backed implementation
    (``boto3`` for AWS KMS, ``google-cloud-kms``, etc.) — the
    Protocol stays the same.
    """

    def __init__(self, keys: dict[str, bytes]) -> None:
        for key_id, key in keys.items():
            if len(key) != HmacStreamCipher.KEY_SIZE:
                raise ValueError(
                    f"key {key_id!r} must be {HmacStreamCipher.KEY_SIZE} bytes, got {len(key)}"
                )
        self._keys = dict(keys)

    @property
    def key_ids(self) -> list[str]:
        return sorted(self._keys)

    def cipher_for(self, key_id: str) -> HmacStreamCipher:
        if key_id not in self._keys:
            raise KeyError(f"no key registered for {key_id!r}")
        return HmacStreamCipher(self._keys[key_id])


def _validate_policies(policies: dict[str, str], km: KeyManager) -> None:
    missing = [c for c in SENSITIVE_COLUMNS if c not in policies]
    if missing:
        raise ValueError(f"policies missing key_id for columns: {missing}")
    for column, key_id in policies.items():
        if key_id not in km.key_ids:
            raise KeyError(f"column {column!r} policy references unknown key_id {key_id!r}")


def cccd_index_hash(cccd: str) -> str:
    """Stable hex SHA-256 of the CCCD — safe to index in plaintext."""
    return hashlib.sha256(cccd.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EncryptedCitizenRecord:
    """Citizen record with every PII field as opaque ciphertext bytes.

    ``cccd_index_hash`` is the *only* plaintext field, and it's a
    one-way hash — enough to support exact-match index lookups
    without revealing the CCCD itself.

    ``expires_at_ciphertext`` is the encryption of an empty bytes
    blob when the original record had ``expires_at = None``. Length
    after AEAD framing is constant; nothing leaks about the value.
    """

    cccd_index_hash: str
    cccd_ciphertext: bytes
    full_name_ciphertext: bytes
    date_of_birth_ciphertext: bytes
    gender_ciphertext: bytes
    hometown_province_code_ciphertext: bytes
    place_of_residence_ciphertext: bytes
    issued_at_ciphertext: bytes
    expires_at_ciphertext: bytes  # b"" plaintext signals "no expiry"


def _encrypt_field(km: KeyManager, key_id: str, value: bytes) -> bytes:
    return km.cipher_for(key_id).encrypt(value)


def _decrypt_field(km: KeyManager, key_id: str, blob: bytes) -> bytes:
    return km.cipher_for(key_id).decrypt(blob)


def encrypt_record(
    record: CitizenRecord,
    km: KeyManager,
    policies: dict[str, str],
) -> EncryptedCitizenRecord:
    """Encrypt every PII column per the supplied ``{column: key_id}`` mapping."""
    _validate_policies(policies, km)

    def _enc(col: str, value: str) -> bytes:
        return _encrypt_field(km, policies[col], value.encode("utf-8"))

    expires_payload = (
        b"" if record.expires_at is None else record.expires_at.isoformat().encode("utf-8")
    )
    return EncryptedCitizenRecord(
        cccd_index_hash=cccd_index_hash(record.cccd),
        cccd_ciphertext=_enc("cccd", record.cccd),
        full_name_ciphertext=_enc("full_name", record.full_name),
        date_of_birth_ciphertext=_enc("date_of_birth", record.date_of_birth.isoformat()),
        gender_ciphertext=_enc("gender", record.gender.value),
        hometown_province_code_ciphertext=_enc(
            "hometown_province_code", record.hometown_province_code
        ),
        place_of_residence_ciphertext=_enc("place_of_residence", record.place_of_residence),
        issued_at_ciphertext=_enc("issued_at", record.issued_at.isoformat()),
        expires_at_ciphertext=_encrypt_field(km, policies["expires_at"], expires_payload),
    )


def decrypt_record(
    enc: EncryptedCitizenRecord,
    km: KeyManager,
    policies: dict[str, str],
) -> CitizenRecord:
    """Inverse of :func:`encrypt_record`."""
    _validate_policies(policies, km)

    def _dec(col: str, blob: bytes) -> str:
        return _decrypt_field(km, policies[col], blob).decode("utf-8")

    cccd = _dec("cccd", enc.cccd_ciphertext)
    expires_raw = _decrypt_field(km, policies["expires_at"], enc.expires_at_ciphertext)
    expires_at = None if expires_raw == b"" else date.fromisoformat(expires_raw.decode("utf-8"))
    return CitizenRecord(
        cccd=cccd,
        full_name=_dec("full_name", enc.full_name_ciphertext),
        date_of_birth=date.fromisoformat(_dec("date_of_birth", enc.date_of_birth_ciphertext)),
        gender=Gender(_dec("gender", enc.gender_ciphertext)),
        hometown_province_code=_dec(
            "hometown_province_code", enc.hometown_province_code_ciphertext
        ),
        place_of_residence=_dec("place_of_residence", enc.place_of_residence_ciphertext),
        issued_at=date.fromisoformat(_dec("issued_at", enc.issued_at_ciphertext)),
        expires_at=expires_at,
    )


__all__ = [
    "SENSITIVE_COLUMNS",
    "EncryptedCitizenRecord",
    "KeyManager",
    "cccd_index_hash",
    "decrypt_record",
    "encrypt_record",
]
