"""Top-level address parser — raw string in, ``ParsedAddress`` out.

Algorithm:

1. **Tokenise** on commas / slashes.
2. **Normalise** each token (lowercase, expand abbreviations,
   diacritic-fold).
3. **Walk tokens right-to-left** — VN addresses are conventionally
   ordered most-specific to most-general, with the province being
   the last token.
4. For each token, attempt to match against the appropriate level:
   PROVINCE first (rightmost), then DISTRICT scoped to that province,
   then WARD scoped to that district.
5. Try **EXACT** match (diacritic-folded equality), then **FUZZY**
   (Levenshtein ≤ 2) as fallback.
6. Whatever tokens precede the first matched admin unit are the
   ``street`` field.
"""

from __future__ import annotations

from vnaddr.distance import find_closest
from vnaddr.normalize import fold_diacritics, normalise, tokens
from vnaddr.schema import (
    AdminLevel,
    AdminUnit,
    MatchedToken,
    MatchKind,
    ParsedAddress,
)
from vnaddr.units import all_units, by_code, by_level, by_parent

_FUZZY_MAX_DISTANCE = 2


# ---- Pre-built lookup indices for each level ---------------------------------


def _index_for_level(level: AdminLevel) -> dict[str, AdminUnit]:
    """Map normalised-folded name → unit, for one administrative level."""
    return {fold_diacritics(u.name_vi): u for u in by_level(level)}


_PROVINCE_INDEX = _index_for_level(AdminLevel.PROVINCE)


def _index_for_parent(parent_code: str) -> dict[str, AdminUnit]:
    """Map normalised-folded child-name → unit, for one parent code."""
    return {fold_diacritics(u.name_vi): u for u in by_parent(parent_code)}


def _strip_admin_prefix(folded_token: str) -> str:
    """Strip a leading 'tinh ' / 'thanh pho ' / 'quan ' etc.

    Many users type ``"Hồ Chí Minh"`` instead of ``"Thành phố Hồ
    Chí Minh"``; we normalise both sides by removing the prefix
    so the comparison works.
    """
    prefixes = (
        "thanh pho ",
        "tinh ",
        "quan ",
        "huyen ",
        "thi xa ",
        "thi tran ",
        "phuong ",
        "xa ",
    )
    for p in prefixes:
        if folded_token.startswith(p):
            return folded_token[len(p) :]
    return folded_token


def _match_one(
    token: str,
    candidates: dict[str, AdminUnit],
) -> MatchedToken | None:
    """Attempt to match a single normalised token against an index.

    Tries exact match first, then strips admin prefixes from both
    sides, then falls back to Levenshtein fuzzy match.
    """
    if not token:
        return None
    # 1. Exact match
    if token in candidates:
        u = candidates[token]
        return MatchedToken(
            raw_token=token,
            matched_code=u.code,
            matched_name=u.name_vi,
            kind=MatchKind.EXACT,
        )
    # 2. Try after stripping the leading admin prefix from the token.
    stripped_token = _strip_admin_prefix(token)
    if stripped_token != token:
        # Build a candidate map keyed by stripped names too.
        for cand_name, unit in candidates.items():
            if _strip_admin_prefix(cand_name) == stripped_token:
                return MatchedToken(
                    raw_token=token,
                    matched_code=unit.code,
                    matched_name=unit.name_vi,
                    kind=MatchKind.EXACT,
                )
    # 3. Fuzzy fallback over BOTH full and stripped candidate names.
    full_names = list(candidates.keys())
    closest_full = find_closest(token, full_names, max_distance=_FUZZY_MAX_DISTANCE)
    stripped_candidates = {_strip_admin_prefix(k): v for k, v in candidates.items()}
    closest_stripped = find_closest(
        stripped_token,
        list(stripped_candidates.keys()),
        max_distance=_FUZZY_MAX_DISTANCE,
    )
    # Prefer whichever has the lower distance.
    best: tuple[str, int, dict[str, AdminUnit]] | None = None
    if closest_full is not None:
        best = (closest_full[0], closest_full[1], candidates)
    if closest_stripped is not None and (best is None or closest_stripped[1] < best[1]):
        best = (closest_stripped[0], closest_stripped[1], stripped_candidates)
    if best is None:
        return None
    matched_name_norm, distance, lookup = best
    unit = lookup[matched_name_norm]
    return MatchedToken(
        raw_token=token,
        matched_code=unit.code,
        matched_name=unit.name_vi,
        kind=MatchKind.FUZZY,
        edit_distance=distance,
    )


def parse(text: str) -> ParsedAddress:
    """Parse a raw VN address into a ``ParsedAddress``.

    Walks the comma-split tokens from right to left, matching
    province → district → ward in turn.
    """
    raw_tokens = tokens(text)
    if not raw_tokens:
        return ParsedAddress(raw_input=text)

    province_match: MatchedToken | None = None
    district_match: MatchedToken | None = None
    ward_match: MatchedToken | None = None

    # Walk right-to-left, consuming tokens.
    remaining = list(raw_tokens)
    # 1. Province (last token)
    if remaining:
        candidate = normalise(remaining[-1])
        match = _match_one(candidate, _PROVINCE_INDEX)
        if match is not None:
            province_match = match
            remaining.pop()
    # 2. District (next token, scoped to province if known)
    if remaining and province_match is not None:
        candidate = normalise(remaining[-1])
        district_index = _index_for_parent(province_match.matched_code)
        if district_index:
            match = _match_one(candidate, district_index)
            if match is not None:
                district_match = match
                remaining.pop()
    elif remaining:
        # Province not known — try all districts.
        candidate = normalise(remaining[-1])
        all_districts = {fold_diacritics(u.name_vi): u for u in by_level(AdminLevel.DISTRICT)}
        match = _match_one(candidate, all_districts)
        if match is not None:
            district_match = match
            remaining.pop()
            # Backfill the province from the matched district.
            parent = by_code(match.matched_code.split(":")[0])
            if parent is not None:
                province_match = MatchedToken(
                    raw_token="",
                    matched_code=parent.code,
                    matched_name=parent.name_vi,
                    kind=MatchKind.ABBREV,
                )
    # 3. Ward (next token, scoped to district if known)
    if remaining and district_match is not None:
        candidate = normalise(remaining[-1])
        ward_index = _index_for_parent(district_match.matched_code)
        if ward_index:
            match = _match_one(candidate, ward_index)
            if match is not None:
                ward_match = match
                remaining.pop()
    # 4. Anything left is the street.
    street = ", ".join(remaining)
    return ParsedAddress(
        raw_input=text,
        street=street,
        ward=ward_match,
        district=district_match,
        province=province_match,
    )


def list_units() -> tuple[AdminUnit, ...]:
    """Re-export ``units.all_units`` for convenience."""
    return all_units()


__all__ = ["list_units", "parse"]
