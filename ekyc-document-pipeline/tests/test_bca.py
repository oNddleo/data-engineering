"""BCA mock database tests."""

from __future__ import annotations

import pytest

from ekycpipe.bca import BCADatabase

from ._fixtures import hcm_male_1995_serial, hn_female_2002_serial, make_bca


def test_empty_db():
    db = BCADatabase([])
    assert db.size == 0
    assert db.lookup("any") is None


def test_lookup_returns_record():
    r = make_bca()
    db = BCADatabase([r])
    assert db.lookup(r.cccd) == r


def test_contains():
    r = make_bca()
    db = BCADatabase([r])
    assert db.contains(r.cccd)
    assert not db.contains("000000000000")


def test_duplicate_cccd_raises():
    r1 = make_bca(cccd=hcm_male_1995_serial(), full_name="A")
    r2 = make_bca(cccd=hcm_male_1995_serial(), full_name="B")
    with pytest.raises(ValueError):
        BCADatabase([r1, r2])


def test_size_reflects_loaded():
    r1 = make_bca(cccd=hcm_male_1995_serial())
    r2 = make_bca(cccd=hn_female_2002_serial())
    db = BCADatabase([r1, r2])
    assert db.size == 2
