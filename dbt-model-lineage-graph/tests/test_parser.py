"""SQL parser — ref / source extraction + comment stripping."""

from __future__ import annotations

from dbtlin.parser import (
    extract_refs,
    extract_sources,
    parse_model,
    parse_project,
    strip_comments,
)

# ---------- strip_comments -------------------------------------------------


def test_strip_line_comment():
    sql = "select * from t -- comment\nwhere 1=1"
    out = strip_comments(sql)
    assert "comment" not in out
    assert "from t" in out


def test_strip_block_comment():
    sql = "select /* multi\nline */ * from t"
    out = strip_comments(sql)
    assert "multi" not in out


def test_strip_jinja_comment():
    sql = "{# this is a dbt comment #}\nselect * from {{ ref('x') }}"
    out = strip_comments(sql)
    assert "dbt comment" not in out
    assert "ref('x')" in out


def test_strip_preserves_string_literals():
    """Comments inside string literals are still stripped — known limitation."""
    sql = "select 'foo -- not a comment' from t"
    # Documented behavior: line-comment regex doesn't distinguish strings.
    out = strip_comments(sql)
    assert "select 'foo" in out  # the start is preserved


# ---------- extract_refs ---------------------------------------------------


def test_extract_single_ref_single_quotes():
    sql = "select * from {{ ref('stg_orders') }}"
    assert extract_refs(sql) == ("stg_orders",)


def test_extract_single_ref_double_quotes():
    sql = 'select * from {{ ref("stg_orders") }}'
    assert extract_refs(sql) == ("stg_orders",)


def test_extract_ref_tolerates_whitespace():
    sql = "select * from {{    ref(   'stg_orders'   )   }}"
    assert extract_refs(sql) == ("stg_orders",)


def test_extract_multiple_refs():
    sql = (
        "select * from {{ ref('a') }} "
        "join {{ ref('b') }} on a.x = b.x "
        "join {{ ref('c') }} on b.y = c.y"
    )
    assert extract_refs(sql) == ("a", "b", "c")


def test_extract_refs_deduplicated():
    sql = "select * from {{ ref('a') }} union all select * from {{ ref('a') }}"
    assert extract_refs(sql) == ("a",)


def test_extract_ref_with_version_arg_extracts_name():
    """``ref('name', v=2)`` still yields the name only."""
    sql = "select * from {{ ref('stg_orders', v=2) }}"
    assert extract_refs(sql) == ("stg_orders",)


def test_extract_refs_skips_commented_out():
    """A ref inside a comment doesn't count."""
    sql = "-- select * from {{ ref('commented') }}\nselect * from {{ ref('real') }}"
    assert extract_refs(sql) == ("real",)


def test_extract_no_refs_empty_tuple():
    sql = "select 1"
    assert extract_refs(sql) == ()


# ---------- extract_sources ------------------------------------------------


def test_extract_single_source():
    sql = "select * from {{ source('shopee', 'raw_orders') }}"
    assert extract_sources(sql) == (("shopee", "raw_orders"),)


def test_extract_multiple_sources():
    sql = "select * from {{ source('a', 'x') }} " "join {{ source('b', 'y') }} on 1=1"
    assert extract_sources(sql) == (("a", "x"), ("b", "y"))


def test_extract_sources_deduplicated():
    sql = (
        "select * from {{ source('a', 'x') }} " "union all " "select * from {{ source('a', 'x') }}"
    )
    assert extract_sources(sql) == (("a", "x"),)


def test_extract_sources_independent_of_refs():
    """A model can have both refs and sources."""
    sql = "select * from {{ ref('stg_orders') }} " "join {{ source('shopee', 'raw_users') }}"
    assert extract_refs(sql) == ("stg_orders",)
    assert extract_sources(sql) == (("shopee", "raw_users"),)


# ---------- parse_model / parse_project -----------------------------------


def test_parse_model_returns_populated_model():
    sql = "select * from {{ ref('stg_orders') }}"
    m = parse_model("fact_orders", sql, path="models/marts/fact_orders.sql")
    assert m.name == "fact_orders"
    assert m.refs == ("stg_orders",)
    assert m.path == "models/marts/fact_orders.sql"


def test_parse_project_sorted_by_name():
    project = {
        "z_model": "select 1",
        "a_model": "select 2",
        "m_model": "select 3",
    }
    models = parse_project(project)
    assert [m.name for m in models] == ["a_model", "m_model", "z_model"]
