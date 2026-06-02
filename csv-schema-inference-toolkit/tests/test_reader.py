"""CSV reader: delimiter sniffing, header detection, full read."""

from __future__ import annotations

from csvinf.reader import read, sniff_delimiter, sniff_has_header


def test_sniff_delimiter_comma():
    text = "a,b,c\n1,2,3\n4,5,6\n"
    assert sniff_delimiter(text) == ","


def test_sniff_delimiter_semicolon():
    text = "a;b;c\n1;2;3\n4;5;6\n"
    assert sniff_delimiter(text) == ";"


def test_sniff_delimiter_tab():
    text = "a\tb\tc\n1\t2\t3\n"
    assert sniff_delimiter(text) == "\t"


def test_sniff_delimiter_pipe():
    text = "a|b|c\n1|2|3\n"
    assert sniff_delimiter(text) == "|"


def test_sniff_delimiter_empty_returns_comma():
    assert sniff_delimiter("") == ","


def test_sniff_delimiter_prefers_consistent():
    """A delimiter that produces inconsistent widths is penalised."""
    # commas are everywhere but inconsistent; semicolons are consistent.
    text = "a;b;c\n" "1,2,3,4,5,6;hello;world\n" "7,8;hi;ok\n" "9,1,2,3;x;y\n"
    # Semicolon yields 3 cols each row; comma yields varying widths.
    assert sniff_delimiter(text) == ";"


def test_sniff_has_header_true():
    text = "name,age,dob\n" "Alice,30,1995-06-15\n" "Bob,25,2000-01-01\n"
    assert sniff_has_header(text, ",") is True


def test_sniff_has_header_false_all_numeric():
    text = "1,2,3\n4,5,6\n7,8,9\n"
    assert sniff_has_header(text, ",") is False


def test_sniff_has_header_false_single_line():
    assert sniff_has_header("a,b,c\n", ",") is False


def test_read_with_header():
    text = "name,age\nAlice,30\nBob,25\n"
    rr = read(text)
    assert rr.has_header
    assert rr.column_names == ("name", "age")
    assert rr.rows == (("Alice", "30"), ("Bob", "25"))


def test_read_without_header():
    text = "1,2,3\n4,5,6\n"
    rr = read(text)
    assert rr.has_header is False
    assert rr.column_names == ("col_0", "col_1", "col_2")
    assert len(rr.rows) == 2


def test_read_max_rows():
    text = "a,b\n1,2\n3,4\n5,6\n7,8\n"
    rr = read(text, max_rows=2)
    assert len(rr.rows) == 2


def test_read_empty_text():
    rr = read("")
    assert rr.column_names == ()
    assert rr.rows == ()


def test_read_with_quoted_field():
    """Commas inside quoted strings don't split the row."""
    text = 'name,note\nAlice,"hello, world"\n'
    rr = read(text)
    assert rr.rows[0] == ("Alice", "hello, world")


def test_read_semicolon_delimited():
    text = "name;city\nNguyễn;HCM\nTrần;HN\n"
    rr = read(text)
    assert rr.delimiter == ";"
    assert rr.rows == (("Nguyễn", "HCM"), ("Trần", "HN"))
