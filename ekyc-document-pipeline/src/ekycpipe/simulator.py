"""Seeded synthetic eKYC data — citizens, OCR results, BCA records.

The simulator's job is to produce realistic-looking but fully
synthetic citizens whose CCCD numbers parse cleanly, whose
BCA-side record agrees with the OCR side (for the happy path), and
whose `image` byte buffer is what the :class:`MockOCREngine`
looks up against to return the canned OCR result.

We also support a small set of *fraud-flavoured* anomaly injections
that the validation rules should catch:

* ``"name_mismatch"`` — OCR name differs from BCA name.
* ``"dob_mismatch"`` — OCR DOB year differs from BCA / CCCD.
* ``"gender_mismatch"`` — OCR gender differs from CCCD encoding.
* ``"not_in_bca"`` — citizen exists in OCR but not in BCA registry.
* ``"bad_cccd"`` — OCR returns a CCCD that fails the format check.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from ekycpipe.bca import BCARecord
from ekycpipe.cccd import build_cccd
from ekycpipe.provinces import PROVINCE_CODES
from ekycpipe.schema import Gender, OCRResult

_FIRST_NAMES_MALE = (
    "An",
    "Bình",
    "Cường",
    "Dũng",
    "Đạt",
    "Hùng",
    "Khôi",
    "Long",
    "Minh",
    "Nam",
    "Phong",
    "Quang",
    "Sơn",
    "Tuấn",
    "Việt",
)
_FIRST_NAMES_FEMALE = (
    "Anh",
    "Bích",
    "Chi",
    "Dung",
    "Hà",
    "Hương",
    "Lan",
    "Linh",
    "Mai",
    "Ngọc",
    "Phương",
    "Quỳnh",
    "Thảo",
    "Trang",
    "Vy",
)
_MIDDLE_NAMES = ("Văn", "Thị", "Hữu", "Đức", "Quốc", "Minh", "Anh", "Thanh")
_LAST_NAMES = (
    "Nguyễn",
    "Trần",
    "Lê",
    "Phạm",
    "Hoàng",
    "Vũ",
    "Đặng",
    "Bùi",
    "Đỗ",
    "Hồ",
    "Ngô",
    "Dương",
    "Lý",
)


def _random_name(rng: random.Random, gender: Gender) -> str:
    last = rng.choice(_LAST_NAMES)
    middle = rng.choice(_MIDDLE_NAMES)
    first = rng.choice(_FIRST_NAMES_MALE if gender is Gender.MALE else _FIRST_NAMES_FEMALE)
    return f"{last} {middle} {first}"


def _random_address(rng: random.Random) -> str:
    street_no = rng.randint(1, 250)
    street = rng.choice(
        ("Lê Lợi", "Trần Hưng Đạo", "Nguyễn Trãi", "Hai Bà Trưng", "Lý Thường Kiệt")
    )
    ward = rng.choice(("P. Bến Nghé", "P. Bến Thành", "P. Đa Kao", "P. Cầu Ông Lãnh"))
    district = rng.choice(("Q. 1", "Q. 3", "Q. 5", "Q. Bình Thạnh"))
    return f"{street_no} {street}, {ward}, {district}"


def _random_birth(rng: random.Random) -> date:
    year = rng.randint(1970, 2005)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return date(year, month, day)


def _make_synthetic_citizen(
    rng: random.Random,
    *,
    serial_seq: int,
) -> tuple[bytes, OCRResult, BCARecord]:
    """Produce one consistent (image_id, OCRResult, BCARecord) tuple."""
    gender = Gender.MALE if rng.random() < 0.5 else Gender.FEMALE
    full_name = _random_name(rng, gender)
    dob = _random_birth(rng)
    province = rng.choice(list(PROVINCE_CODES.keys()))
    serial = f"{serial_seq:06d}"
    cccd = build_cccd(province_code=province, gender=gender, birth_year=dob.year, serial=serial)
    issued = date(2023, rng.randint(1, 12), rng.randint(1, 28))
    expires = issued + timedelta(days=365 * 10)
    image = f"IMG-{cccd}".encode()
    ocr = OCRResult(
        cccd=cccd,
        full_name=full_name,
        date_of_birth=dob.strftime("%d/%m/%Y"),
        gender="Nam" if gender is Gender.MALE else "Nữ",
        hometown=PROVINCE_CODES[province],
        place_of_residence=_random_address(rng),
        issued_at=issued.strftime("%d/%m/%Y"),
        expires_at=expires.strftime("%d/%m/%Y"),
        confidence=rng.uniform(0.85, 0.99),
    )
    bca = BCARecord(
        cccd=cccd,
        full_name=full_name,
        date_of_birth=dob,
        gender=gender,
        hometown_province_code=province,
    )
    return image, ocr, bca


def _apply_anomaly(
    rng: random.Random,
    anomaly: str,
    image: bytes,
    ocr: OCRResult,
    bca: BCARecord,
) -> tuple[bytes, OCRResult, BCARecord | None]:
    if anomaly == "name_mismatch":
        bad_name = "Người " + str(rng.randint(1000, 9999))
        return (
            image,
            OCRResult(
                cccd=ocr.cccd,
                full_name=bad_name,
                date_of_birth=ocr.date_of_birth,
                gender=ocr.gender,
                hometown=ocr.hometown,
                place_of_residence=ocr.place_of_residence,
                issued_at=ocr.issued_at,
                expires_at=ocr.expires_at,
                confidence=ocr.confidence,
            ),
            bca,
        )
    if anomaly == "dob_mismatch":
        return (
            image,
            OCRResult(
                cccd=ocr.cccd,
                full_name=ocr.full_name,
                date_of_birth="01/01/1980",  # rarely matches real DOB
                gender=ocr.gender,
                hometown=ocr.hometown,
                place_of_residence=ocr.place_of_residence,
                issued_at=ocr.issued_at,
                expires_at=ocr.expires_at,
                confidence=ocr.confidence,
            ),
            bca,
        )
    if anomaly == "gender_mismatch":
        flipped = "Nữ" if ocr.gender == "Nam" else "Nam"
        return (
            image,
            OCRResult(
                cccd=ocr.cccd,
                full_name=ocr.full_name,
                date_of_birth=ocr.date_of_birth,
                gender=flipped,
                hometown=ocr.hometown,
                place_of_residence=ocr.place_of_residence,
                issued_at=ocr.issued_at,
                expires_at=ocr.expires_at,
                confidence=ocr.confidence,
            ),
            bca,
        )
    if anomaly == "not_in_bca":
        return image, ocr, None
    if anomaly == "bad_cccd":
        return (
            image,
            OCRResult(
                cccd="000000000000",  # province 000 isn't valid
                full_name=ocr.full_name,
                date_of_birth=ocr.date_of_birth,
                gender=ocr.gender,
                hometown=ocr.hometown,
                place_of_residence=ocr.place_of_residence,
                issued_at=ocr.issued_at,
                expires_at=ocr.expires_at,
                confidence=ocr.confidence,
            ),
            bca,
        )
    raise ValueError(f"unknown anomaly kind: {anomaly!r}")


def generate(
    *,
    n_citizens: int = 10,
    seed: int = 0,
    anomalies: list[str] | None = None,
) -> tuple[dict[bytes, OCRResult], list[BCARecord]]:
    """Produce ``n_citizens`` clean records + optional anomalous extras.

    Returns ``(image_to_ocr, bca_records)`` — the first plugs into
    :class:`ekycpipe.ocr.MockOCREngine`, the second into
    :class:`ekycpipe.bca.BCADatabase`.
    """
    rng = random.Random(seed)
    image_to_ocr: dict[bytes, OCRResult] = {}
    bca_records: list[BCARecord] = []
    serial = 1
    for _ in range(n_citizens):
        image, ocr, bca = _make_synthetic_citizen(rng, serial_seq=serial)
        serial += 1
        image_to_ocr[image] = ocr
        bca_records.append(bca)
    for anomaly in anomalies or []:
        image, ocr, bca = _make_synthetic_citizen(rng, serial_seq=serial)
        serial += 1
        image, ocr_mut, bca_mut = _apply_anomaly(rng, anomaly, image, ocr, bca)
        image_to_ocr[image] = ocr_mut
        if bca_mut is not None:
            bca_records.append(bca_mut)
    return image_to_ocr, bca_records


__all__ = ["generate"]
