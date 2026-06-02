"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from bloomdedup.io_jsonl import dump_keys, load_keys


def test_roundtrip() -> None:
    keys = ["a", "b", "c"]
    assert load_keys(dump_keys(keys)) == keys


def test_empty() -> None:
    assert load_keys(dump_keys([])) == []


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load_keys("[1,2,3]\n")


def test_load_rejects_missing_key() -> None:
    with pytest.raises((KeyError, TypeError)):
        load_keys('{"id":1}\n')


def test_unicode_passthrough() -> None:
    keys = ["café", "ngôn ngữ", "tỷ giá"]
    assert load_keys(dump_keys(keys)) == keys
