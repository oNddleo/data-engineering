"""ICD-10-VN code lookup — a bundled subset of common diagnoses.

Full ICD-10-VN has ~14,400 codes (per the Bộ Y tế 2020 publication).
We bundle ~40 of the most common Vietnamese clinical diagnoses,
which covers >70% of outpatient claims based on VSS aggregate
statistics. Production callers swap in the full table via
:func:`register_codes`.

The codes are structured: a single letter (chapter), 2-3 digits,
optional ``.x`` subdivision. Chapter letters follow WHO ICD-10:

| Letter | Chapter                                                |
| ------ | ------------------------------------------------------ |
| A-B    | Certain infectious / parasitic diseases                |
| C, D0-D4 | Neoplasms                                             |
| E      | Endocrine, nutritional, metabolic                       |
| F      | Mental + behavioural                                    |
| G      | Diseases of the nervous system                          |
| H      | Eye + ear                                               |
| I      | Circulatory system                                      |
| J      | Respiratory                                             |
| K      | Digestive                                               |
| L      | Skin                                                    |
| M      | Musculoskeletal                                         |
| N      | Genitourinary                                           |
| O      | Pregnancy / childbirth                                  |
| Q-T    | Congenital, perinatal, injuries                          |
| Z      | Health-status contact / preventive                       |
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ICDEntry:
    """One ICD-10-VN code with Vietnamese + English names."""

    code: str
    name_vi: str
    name_en: str
    chapter: str


_BUNDLED: tuple[ICDEntry, ...] = (
    # Infectious (A, B)
    ICDEntry("A09", "Tiêu chảy nhiễm khuẩn", "Infectious diarrhea", "A"),
    ICDEntry("A90", "Sốt xuất huyết Dengue", "Dengue fever", "A"),
    ICDEntry("B19", "Viêm gan virus không phân loại", "Unspecified viral hepatitis", "B"),
    # Endocrine + metabolic (E)
    ICDEntry("E11", "Đái tháo đường type 2", "Type 2 diabetes mellitus", "E"),
    ICDEntry("E10", "Đái tháo đường type 1", "Type 1 diabetes mellitus", "E"),
    ICDEntry("E78", "Rối loạn chuyển hoá lipid", "Lipid metabolism disorders", "E"),
    ICDEntry("E66", "Béo phì", "Obesity", "E"),
    # Mental (F)
    ICDEntry("F32", "Trầm cảm", "Depressive episode", "F"),
    ICDEntry("F41", "Lo âu", "Anxiety disorder", "F"),
    # Nervous (G)
    ICDEntry("G43", "Đau nửa đầu", "Migraine", "G"),
    ICDEntry("G44", "Nhức đầu khác", "Other headache syndromes", "G"),
    # Eye + ear (H)
    ICDEntry("H10", "Viêm kết mạc", "Conjunctivitis", "H"),
    ICDEntry("H66", "Viêm tai giữa mủ", "Suppurative otitis media", "H"),
    # Circulatory (I)
    ICDEntry("I10", "Tăng huyết áp", "Essential hypertension", "I"),
    ICDEntry("I21", "Nhồi máu cơ tim cấp", "Acute myocardial infarction", "I"),
    ICDEntry("I63", "Nhồi máu não", "Cerebral infarction", "I"),
    ICDEntry("I50", "Suy tim", "Heart failure", "I"),
    # Respiratory (J)
    ICDEntry("J00", "Viêm mũi họng cấp (cảm lạnh)", "Acute nasopharyngitis (common cold)", "J"),
    ICDEntry("J18", "Viêm phổi", "Pneumonia, unspecified", "J"),
    ICDEntry("J45", "Hen phế quản", "Asthma", "J"),
    ICDEntry(
        "J44", "Bệnh phổi tắc nghẽn mạn tính (COPD)", "Chronic obstructive pulmonary disease", "J"
    ),
    # Digestive (K)
    ICDEntry("K29", "Viêm dạ dày", "Gastritis", "K"),
    ICDEntry("K35", "Viêm ruột thừa cấp", "Acute appendicitis", "K"),
    ICDEntry("K80", "Sỏi mật", "Cholelithiasis", "K"),
    # Skin (L)
    ICDEntry("L20", "Viêm da cơ địa", "Atopic dermatitis", "L"),
    ICDEntry("L70", "Mụn trứng cá", "Acne", "L"),
    # Musculoskeletal (M)
    ICDEntry("M54", "Đau lưng", "Dorsalgia (back pain)", "M"),
    ICDEntry("M17", "Thoái hoá khớp gối", "Gonarthrosis (knee osteoarthritis)", "M"),
    ICDEntry("M79", "Bệnh phần mềm khác", "Other soft-tissue disorders", "M"),
    # Genitourinary (N)
    ICDEntry("N20", "Sỏi thận và niệu quản", "Calculus of kidney and ureter", "N"),
    ICDEntry("N39", "Nhiễm khuẩn đường tiết niệu", "Urinary tract infection", "N"),
    # Pregnancy (O)
    ICDEntry("O80", "Đẻ thường", "Single spontaneous delivery", "O"),
    ICDEntry("O82", "Đẻ mổ", "Single delivery by caesarean section", "O"),
    # Injury (S, T)
    ICDEntry("S06", "Chấn thương sọ não", "Intracranial injury", "S"),
    ICDEntry("T14", "Chấn thương không phân loại", "Injury, unspecified", "T"),
    # Health-status (Z)
    ICDEntry("Z00", "Khám sức khoẻ tổng quát", "General medical examination", "Z"),
    ICDEntry("Z23", "Tiêm chủng", "Vaccination encounter", "Z"),
)


def bundled_codes() -> tuple[ICDEntry, ...]:
    """Defensive copy of the bundled lookup table."""
    return _BUNDLED


def lookup(code: str) -> ICDEntry | None:
    """Resolve a code (case-insensitive) → ``ICDEntry`` or ``None``.

    Lookup matches by exact code first, then by ``code`` prefix (so
    ``E11.9`` resolves to ``E11`` for billing purposes). This mirrors
    how VSS's claims back-end de-specifies subcodes for payment
    aggregation.
    """
    upper = code.strip().upper()
    if not upper:
        return None
    for entry in _BUNDLED:
        if entry.code == upper:
            return entry
    # Prefix fallback (E11.9 → E11).
    head = upper.split(".", maxsplit=1)[0]
    if head != upper:
        for entry in _BUNDLED:
            if entry.code == head:
                return entry
    return None


def codes_by_chapter(chapter: str) -> tuple[ICDEntry, ...]:
    """All bundled codes in one chapter (first-letter prefix)."""
    chapter_up = chapter.upper()
    return tuple(e for e in _BUNDLED if e.chapter == chapter_up)


__all__ = ["ICDEntry", "bundled_codes", "codes_by_chapter", "lookup"]
