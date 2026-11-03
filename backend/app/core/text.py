"""Chuẩn hóa văn bản dùng chung cho từ điển và truy vấn.

Quy tắc phải giống hệt ``DictionaryProcessor.normalize_text`` trong
``data_processor.py`` của repo để kết quả backend trùng với bản thuật toán
mà nhóm đã viết:

1. Chuẩn hóa Unicode về dạng NFC (tiếng Việt dựng sẵn).
2. Chuyển thành chữ thường.
3. Bỏ mọi ký tự không phải chữ/số/gạch dưới hoặc khoảng trắng.
4. Gộp các khoảng trắng liên tiếp thành một và cắt hai đầu.
"""

from __future__ import annotations

import re
import unicodedata

# Biên dịch một lần: mỗi truy vấn phải chuẩn hóa 23.850 từ khóa nên tốc độ
# của biểu thức chính quy có ảnh hưởng trực tiếp tới thời gian phản hồi.
_PUNCTUATION = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WHITESPACE = re.compile(r"\s+", flags=re.UNICODE)


def normalize_text(text: object) -> str:
    """Trả về dạng chuẩn hóa của ``text``; chuỗi không hợp lệ trả về ``""``."""
    if not isinstance(text, str) or not text:
        return ""
    normalized = unicodedata.normalize("NFC", text).lower()
    normalized = _PUNCTUATION.sub("", normalized)
    return _WHITESPACE.sub(" ", normalized).strip()


def fold_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt (``đ`` → ``d``); độ dài chuỗi NFC không đổi."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d")


def starts_a_word(query: str, keyword: str) -> bool:
    """True nếu ``query`` xuất hiện ở đầu một từ của ``keyword``."""
    return (" " + query) in (" " + keyword)
