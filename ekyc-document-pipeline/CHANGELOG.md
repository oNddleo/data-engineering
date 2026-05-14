# Changelog

## [0.1.0] — 2026-05-14

### Added
- 63-entry province-code registry per Thông tư 07/2016/TT-BCA
  (`PROVINCE_CODES`, `province_name`, `is_valid_province_code`).
- `parse_cccd(cccd)` decodes a 12-digit CCCD into
  `CCCDFields(province_code, gender, century, birth_year_yy, serial)`
  with a `birth_year` derived property. Round-trippable via
  `build_cccd()`. Five gender/century pairs across 19xx–23xx
  (covering CCCDs issued for citizens born in any of five centuries —
  important because the encoding has slots for centuries that don't
  yet exist).
- `Gender` enum; `CCCDFields`, `OCRResult` (with `is_complete`
  property), `CitizenRecord` (with strict invariants — non-empty
  CCCD/name, expires ≥ issued).
- `HmacStreamCipher` — educational AEAD on stdlib only:
  HMAC-SHA256 keystream + Encrypt-then-MAC with random 12-byte
  nonce per encryption and 16-byte truncated authentication tag.
  Constant-time tag verification. `IntegrityError` on tamper.
- `derive_key(passphrase, salt)` — PBKDF2-HMAC-SHA256, 200k iters,
  32-byte output. For demo/test only — production keys come from a
  KMS.
- `KeyManager` — `{key_id: 32-byte key}` registry with
  `cipher_for(key_id)`. Enforces 32-byte key size at construction.
- Column-level encryption with explicit `{column: key_id}` policy:
  - `SENSITIVE_COLUMNS` lists the 8 PII fields we encrypt.
  - `encrypt_record` / `decrypt_record` round-trip a `CitizenRecord`
    into an `EncryptedCitizenRecord`.
  - `cccd_index_hash(cccd)` — stable SHA-256 hex for indexed
    lookup without decryption.
  - `None` `expires_at` encrypted as zero-length plaintext so blob
    length doesn't leak the value.
- `BCADatabase` mock with `lookup(cccd) → BCARecord | None`;
  rejects duplicate CCCDs at construction.
- 4 validation rules + `merge()`:
  - `validate_cccd_format` — CCCD parses cleanly.
  - `validate_ocr_consistency` — OCR DOB year & gender agree with
    CCCD encoding (errors); unparseable OCR fields → warnings.
  - `validate_against_bca` — BCA lookup + cross-check on name
    (case-insensitive), DOB, gender.
- `parse_date_dmy` (dd/mm/yyyy + ISO formats) and `parse_gender_text`
  (Nam/Nữ/Male/Female/M/F/Nu).
- `OCREngine` Protocol + `MockOCREngine` (canned-response by image
  bytes). Production engines satisfy the same Protocol.
- `process_image(image, ocr, bca, key_manager, policies)` —
  end-to-end pipeline. Fail-closed: validation error → encryption
  skipped; the result still carries the OCR + parsed_cccd +
  validation reasons for the UI / audit log.
- Seeded synthetic generator with 5 anomaly injection kinds:
  `name_mismatch`, `dob_mismatch`, `gender_mismatch`, `not_in_bca`,
  `bad_cccd`. Vietnamese first/middle/last name pools matched to
  gender.
- `ekycpipe` CLI with subcommands `info`, `parse-cccd`, `simulate`,
  `run` (`--with-encryption` + `--encryption-seed`),
  `demo-keygen`.
- **112 tests** including 4 Hypothesis properties:
  - `build_cccd → parse_cccd` round-trips for any (province, year
    1900–2299, gender, 6-digit serial)
  - AEAD round-trips arbitrary byte strings up to 200 bytes
  - Encrypted record round-trips arbitrary non-blank printable names
  - Repeated `encrypt()` of same plaintext yields distinct blobs
- mypy `--strict` clean over 12 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `ekyc` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Security notes (important)
- `HmacStreamCipher` is **educational**. It's a defensible AEAD
  construction (encrypt-then-MAC with random nonce + tag), but it
  reuses the same key for both encryption and authentication and
  hand-rolls the counter mode. The `Cipher` Protocol exists so
  production callers can swap in `cryptography.fernet.Fernet` or
  AES-GCM without touching the rest of the codebase.
- `derive_key()` uses 200k PBKDF2 iterations. That's tuned for an
  interactive demo. Re-tune for your threat model before shipping.
- The simulator emits PII-shaped fake data only. Synthetic names
  are deliberately constructed (not lifted from any real list) and
  the CCCD numbers parse cleanly into a fake province/year/serial
  triple that doesn't correspond to any real citizen.

### Notes
- CCCD's century/gender digit slots 4–9 represent centuries 21–23
  that haven't fully arrived yet — but the encoding is part of the
  official schema, so `build_cccd(birth_year=2105)` works and
  round-trips. The same logic accepts up to year 2399.
- BCA cross-check uses case-insensitive name matching; the OCR
  often returns ALL-CAPS while BCA stores title-case.
- Pipeline's `_to_citizen_record` keeps BCA as the authoritative
  source for name/DOB/gender/hometown, and OCR as the source for
  `place_of_residence` / `issued_at` / `expires_at` (fields BCA
  doesn't return).
