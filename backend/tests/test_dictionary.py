"""Kiểm tra nạp và lập chỉ mục từ điển."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.dictionary import EmptyDictionaryError, KeywordDictionary


def test_load_normalizes_and_deduplicates(tmp_path: Path) -> None:
    path = tmp_path / "dictionary.txt"
    path.write_text(
        "Điện thoại Samsung\nđiện  thoại samsung\nĐIỆN THOẠI SAMSUNG!\n\ntai nghe bluetooth\n",
        encoding="utf-8",
    )

    dictionary = KeywordDictionary.from_file(path)

    assert dictionary.keywords == ("tai nghe bluetooth", "điện thoại samsung")
    assert dictionary.stats.size == 2
    assert dictionary.stats.min_length == len("tai nghe bluetooth")
    assert dictionary.stats.max_length == len("điện thoại samsung")
    assert dictionary.stats.load_ms >= 0


def test_by_length_index_matches_keywords() -> None:
    keywords = ["ab", "abc", "abcd", "abcde", "xyz"]
    dictionary = KeywordDictionary(keywords)

    for length, bucket in dictionary.by_length.items():
        assert all(len(keyword) == length for keyword in bucket)
    assert dictionary.lengths == tuple(sorted(dictionary.by_length))
    assert sum(len(bucket) for bucket in dictionary.by_length.values()) == len(dictionary)


def test_skips_invalid_entries() -> None:
    dictionary = KeywordDictionary([None, 123, "   ", "!!!", "Hợp Lệ"])
    assert dictionary.keywords == ("hợp lệ",)


def test_empty_dictionary_raises() -> None:
    with pytest.raises(EmptyDictionaryError):
        KeywordDictionary([])
    with pytest.raises(EmptyDictionaryError):
        KeywordDictionary(["...", "   "])


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        KeywordDictionary.from_file(tmp_path / "khong-ton-tai.txt")
