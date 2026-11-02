"""Kiểm tra chuẩn hóa văn bản."""

from __future__ import annotations

import unicodedata

from app.core.text import normalize_text


def test_lowercase_and_punctuation() -> None:
    assert normalize_text("Điện Thoại, Samsung!") == "điện thoại samsung"


def test_collapses_whitespace() -> None:
    assert normalize_text("  điện \t thoại\n samsung  ") == "điện thoại samsung"


def test_nfc_and_nfd_are_equivalent() -> None:
    composed = "điện thoại"
    decomposed = unicodedata.normalize("NFD", composed)
    assert composed != decomposed  # khác byte nhưng cùng nghĩa
    assert normalize_text(composed) == normalize_text(decomposed)


def test_keeps_underscore_and_digits() -> None:
    assert normalize_text("Iphone_15 Pro Max") == "iphone_15 pro max"


def test_removes_only_punctuation() -> None:
    assert normalize_text("...") == ""
    # Giống hệt DictionaryProcessor gốc: bỏ dấu câu *không* thay bằng khoảng
    # trắng, nên "áo-thun" dính thành "áothun" (đây là hành vi có chủ đích để
    # backend trùng kết quả với bản thuật toán của nhóm).
    assert normalize_text("áo-thun (akko)") == "áothun akko"


def test_invalid_values() -> None:
    assert normalize_text(None) == ""
    assert normalize_text("") == ""
    assert normalize_text(123) == ""
