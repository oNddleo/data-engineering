"""Hypothesis properties — invariants of checks + runner."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from dqkit.checks_generic import not_null, range_int, unique
from dqkit.checks_vn import mst, vn_phone

# ---------- generic ------------------------------------------------------


@given(
    rows=st.lists(
        st.dictionaries(
            keys=st.just("x"),
            values=st.one_of(st.none(), st.text(min_size=0, max_size=5)),
            min_size=1,
            max_size=1,
        ),
        min_size=0,
        max_size=20,
    )
)
@settings(max_examples=100)
def test_not_null_failure_count_matches(rows: list[dict[str, str | None]]) -> None:
    """``not_null`` failures exactly equals the null + empty-string count."""
    expected = sum(1 for r in rows if r.get("x") is None or r.get("x") == "")
    result = not_null()(rows, "x")  # type: ignore[operator]
    assert result.n_failed == expected


@given(
    rows=st.lists(
        st.dictionaries(
            keys=st.just("x"),
            values=st.text(alphabet="abcd", min_size=1, max_size=2),
            min_size=1,
            max_size=1,
        ),
        min_size=0,
        max_size=20,
    )
)
@settings(max_examples=50)
def test_unique_failure_count_matches_duplicates(rows: list[dict[str, str]]) -> None:
    """Failures equal (count - distinct) summed over non-null values."""
    values = [r.get("x") for r in rows]
    distinct = len({v for v in values if v})
    n_present = sum(1 for v in values if v)
    expected = n_present - distinct
    result = unique()(rows, "x")  # type: ignore[operator]
    assert result.n_failed == expected


@given(
    values=st.lists(st.integers(min_value=-1000, max_value=1000), min_size=0, max_size=20),
    lo=st.integers(min_value=-100, max_value=0),
    hi=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=100)
def test_range_int_failure_count(values: list[int], lo: int, hi: int) -> None:
    """range_int counts exactly the out-of-band values."""
    rows = [{"x": v} for v in values]
    expected = sum(1 for v in values if not lo <= v <= hi)
    result = range_int(lo, hi)(rows, "x")  # type: ignore[operator]
    assert result.n_failed == expected


# ---------- VN checks ---------------------------------------------------


@given(prefix=st.text(alphabet="0123456789", min_size=9, max_size=9))
@settings(max_examples=100)
def test_mst_valid_with_computed_check_digit(prefix: str) -> None:
    """For any 9-digit prefix, prefix + computed_check passes ``mst``."""
    from dqkit.checks_vn import _MST_WEIGHTS

    total = sum(int(d) * w for d, w in zip(prefix, _MST_WEIGHTS, strict=True))
    mod = total % 11
    check_digit = 0 if mod == 0 else 10 - mod
    candidate = prefix + str(check_digit)
    result = mst()([{"x": candidate}], "x")  # type: ignore[operator]
    assert result.passed is True


@given(
    prefix=st.sampled_from(["03", "05", "07", "08", "09"]),
    rest=st.text(alphabet="0123456789", min_size=8, max_size=8),
)
@settings(max_examples=50)
def test_vn_phone_accepts_any_valid_mobile(prefix: str, rest: str) -> None:
    """A valid mobile prefix + 8 digits is always accepted."""
    candidate = prefix + rest
    result = vn_phone()([{"x": candidate}], "x")  # type: ignore[operator]
    assert result.passed is True


@given(
    bad_prefix=st.sampled_from(["00", "01", "02", "04", "06"]),
    rest=st.text(alphabet="0123456789", min_size=8, max_size=8),
)
@settings(max_examples=50)
def test_vn_phone_rejects_bad_prefix(bad_prefix: str, rest: str) -> None:
    """Mobile-style number with a non-mobile prefix is rejected.

    (Except ``02`` + 8 digits which is a valid landline — skip that.)
    """
    if bad_prefix == "02":
        return  # 02 + 8 digits = landline; would pass
    candidate = bad_prefix + rest
    result = vn_phone()([{"x": candidate}], "x")  # type: ignore[operator]
    assert result.n_failed == 1
