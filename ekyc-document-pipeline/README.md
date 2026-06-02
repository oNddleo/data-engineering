# ekyc-document-pipeline

Pipeline eKYC cho CCCD/CMND Việt Nam: parse CCCD theo
Thông tư 07/2016/TT-BCA (mã tỉnh + giới tính + thế kỷ + năm sinh
nhúng trong 12 chữ số), OCR Protocol + mock engine, validate
cross-check với BCA dummy DB, lưu PII bằng column-level encryption
(HMAC-based AEAD trên stdlib `hashlib`/`hmac`/`secrets` only).

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Parse CCCD** — 12 chữ số decoded into:
   - 3 đầu = mã tỉnh nơi đăng ký khai sinh (`079` = TP.HCM, `001` = Hà Nội, …)
   - 4th = giới tính + thế kỷ (0/1=Nam/Nữ 19xx, 2/3=Nam/Nữ 20xx, … đến 23xx)
   - 5th–6th = YY (last two of birth year)
   - 7th–12th = serial 6 chữ số
2. **OCR Protocol** — `OCREngine.recognize(image: bytes) → OCRResult`.
   Bundle `MockOCREngine` (lookup canned responses) cho test;
   production swap với PaddleOCR/VietOCR/Tesseract wrapper (cùng
   Protocol).
3. **Validate** (4 rules, có thể compose):
   - CCCD format (12 digits, valid province)
   - OCR ↔ CCCD consistency (DOB year & gender must match CCCD encoding)
   - BCA lookup (CCCD must exist in BCA registry)
   - BCA cross-check (OCR name/DOB/gender must match BCA record)
4. **Encrypt** PII columns sau khi pass validation — column-level
   với per-column key policy. Output `EncryptedCitizenRecord` với
   mọi PII field là ciphertext, chỉ giữ 1 plaintext `cccd_index_hash`
   để index lookup.

Pipeline fail-closed: bất kỳ validation error nào → suppress
encryption + return `PipelineResult.encrypted = None`.

## Crypto — educational HMAC-based AEAD

**Đây là demo, không phải industry-grade.** Production phải dùng
`cryptography.fernet.Fernet` hoặc AES-GCM từ vetted library. Vì
project này zero-deps, ta build AEAD trên stdlib:

```
encrypt(plaintext):
  nonce  = secrets.token_bytes(12)
  ks     = HMAC-SHA256(key, nonce || counter)  for counter = 0, 1, 2…
  ct     = plaintext XOR ks
  tag    = HMAC-SHA256(key, b"AUTH" || nonce || ct)[:16]
  return nonce || ct || tag

decrypt(blob):
  parse nonce, ct, tag → verify tag (constant-time) → XOR ks back
  any tamper → IntegrityError
```

Đặc điểm:
* Encrypt-then-MAC (đúng order).
* Random nonce per encrypt — same plaintext encrypts to different blobs.
* Authentication tag chống tamper (proven by `test_decrypt_rejects_tampered_*`).
* 32-byte keys, 12-byte nonces, 16-byte truncated tags.

## Column-level policy

```python
SENSITIVE_COLUMNS = (
    "cccd", "full_name", "date_of_birth", "gender",
    "hometown_province_code", "place_of_residence",
    "issued_at", "expires_at",
)

km = KeyManager({"K-PII": pii_key_bytes, "K-DOB": dob_key_bytes})
policies = {c: "K-PII" for c in SENSITIVE_COLUMNS}
policies["date_of_birth"] = "K-DOB"  # different team owns DOB key

enc = encrypt_record(citizen, km, policies)
# enc.full_name_ciphertext    — only readable with K-PII
# enc.date_of_birth_ciphertext — only readable with K-DOB
# enc.cccd_index_hash         — public-ish, indexed for lookups
```

If the encryption-decryption keys don't match, AEAD's authentication
tag fails — caught explicitly by `test_decrypt_with_wrong_key_for_column_fails`.

## Components

| Module                | Role                                                                |
| --------------------- | ------------------------------------------------------------------- |
| `ekycpipe.provinces`  | 63-entry NAPAS/BCA province-code registry                            |
| `ekycpipe.cccd`       | `parse_cccd` / `build_cccd` + `CCCDFormatError`                      |
| `ekycpipe.schema`     | `Gender`, `CCCDFields`, `OCRResult`, `CitizenRecord`                 |
| `ekycpipe.crypto`     | `HmacStreamCipher` AEAD + `derive_key` (PBKDF2)                      |
| `ekycpipe.encryption` | `KeyManager`, column-level `encrypt_record`/`decrypt_record`         |
| `ekycpipe.bca`        | Mock `BCADatabase` + `BCARecord`                                     |
| `ekycpipe.validate`   | 3 rules + `merge` + `parse_date_dmy` / `parse_gender_text` helpers   |
| `ekycpipe.ocr`        | `OCREngine` Protocol + `MockOCREngine`                               |
| `ekycpipe.pipeline`   | `process_image(image, ocr, bca, key_manager, policies)`              |
| `ekycpipe.simulator`  | Seeded synthetic citizens + 5 anomaly kinds                          |
| `ekycpipe.cli`        | `ekycpipe info | parse-cccd | simulate | run | demo-keygen`          |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
ekycpipe info

# Decode a CCCD number.
ekycpipe parse-cccd 079095012345
# → province=079 (TP.HCM)  gender=MALE  century=19xx  birth_year=1995  serial=012345

# Generate a synthetic dataset with anomalies.
ekycpipe simulate \
  --citizens 100 \
  --seed 42 \
  --anomalies name_mismatch,bad_cccd \
  --output dataset.json

# Run the pipeline and produce a summary.
ekycpipe run --dataset dataset.json --with-encryption \
  --encryption-seed "secret-passphrase-for-demo"
# → {"processed": 102, "valid": 100, "encrypted": 100, "errors": [...]}

# Generate one fresh 32-byte key.
ekycpipe demo-keygen
# → 64-char hex string
```

End-to-end output on a small synthetic stream (8 clean + 2 anomalies):

```
{
  "processed": 10,
  "valid": 8,
  "encrypted": 8,
  "errors": [
    {"cccd": "027198000009", "error": "name mismatch: OCR='Người 7233' vs BCA='Bùi Thị Chi'"},
    {"cccd": "000000000000", "error": "unknown province code '000' in CCCD '000000000000'"}
  ]
}
```

## Library

```python
from ekycpipe import (
    MockOCREngine, BCADatabase, KeyManager, SENSITIVE_COLUMNS,
    generate, process_image,
)

ocr_map, bca_records = generate(n_citizens=5, seed=42, anomalies=["name_mismatch"])
ocr_engine = MockOCREngine(ocr_map)
bca = BCADatabase(bca_records)
km = KeyManager({"K-PII": b"\xab" * 32})
policies = {c: "K-PII" for c in SENSITIVE_COLUMNS}

for image in ocr_map:
    result = process_image(image, ocr=ocr_engine, bca=bca,
                            key_manager=km, policies=policies)
    if result.validation.is_valid:
        # result.encrypted is the column-encrypted record.
        pass
    else:
        # result.validation.errors lists why it failed.
        pass
```

## Production hardening checklist

This repo is the *structure* of a production eKYC pipeline. To
deploy it for real:

1. **OCR** — wrap PaddleOCR / VietOCR / Tesseract in a class that
   satisfies the `OCREngine` Protocol. The `recognize(image: bytes)
   → OCRResult` contract stays the same.
2. **BCA** — swap `BCADatabase` for an HTTP client to the actual
   BCA verification endpoint. Same `.lookup(cccd) → BCARecord | None`
   surface.
3. **Crypto** — replace `HmacStreamCipher` with `cryptography.fernet.Fernet`
   or AES-GCM. The `Cipher` Protocol is already there. Do **not**
   ship the educational `HmacStreamCipher` to production.
4. **Keys** — wire `KeyManager` to AWS KMS / GCP KMS / HashiCorp
   Vault. The `cipher_for(key_id)` surface stays.
5. **Policy compliance** — make sure your column policies map to
   the data-classification scheme required by Nghị định 13/2023/NĐ-CP
   (DPO sign-off + retention SLAs).

## Quality

```bash
make test       # 112 tests, 4 Hypothesis properties
make type       # mypy --strict
make lint
```

- **112 tests** including 4 Hypothesis properties (CCCD build/parse
  round-trip; AEAD round-trips arbitrary byte strings; encrypted
  record round-trips arbitrary printable names; repeated encrypt()
  always produces distinct blobs).
- mypy `--strict` clean over 12 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `ekyc` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
