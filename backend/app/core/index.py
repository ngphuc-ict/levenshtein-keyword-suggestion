"""Chỉ mục n-gram (trigram) để sinh nhanh tập ứng viên.

Vì sao cần: từ điển có 23.850 từ khóa và rất nhiều từ cùng độ dài, nếu tính
khoảng cách Levenshtein cho tất cả thì mỗi truy vấn mất hàng trăm mili giây.
Chỉ mục trigram giúp loại bỏ phần lớn từ khóa *mà không làm sai kết quả*.

Cơ sở toán học: với mỗi chuỗi, lấy tập trigram sau khi đệm 2 khoảng trắng ở
hai đầu (để bắt cả phần đầu/cuối từ). Một phép chèn, xóa hoặc thay thế ký tự
chỉ có thể phá hủy tối đa 3 trigram của chuỗi gốc. Do đó nếu
``distance(query, keyword) <= d`` thì hai chuỗi phải chia sẻ ít nhất
``|G(query)| - 3*d`` trigram. Đây là điều kiện *cần*, nên dùng nó để lọc
không bao giờ bỏ sót ứng viên thật sự nằm trong ngưỡng ``d``.

Khi ``|G(query)| - 3*d <= 0`` thì điều kiện trên không còn tác dụng; lúc đó
``candidates`` trả về ``None`` và bộ gợi ý chuyển sang quét đầy đủ (chậm hơn
nhưng vẫn đúng) — thường chỉ xảy ra với truy vấn rất ngắn hoặc vô nghĩa.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

QGRAM_SIZE = 3
_PADDING = "  "


def qgrams(text: str) -> set[str]:
    """Tập trigram của ``text`` sau khi đệm khoảng trắng hai đầu."""
    padded = _PADDING + text + _PADDING
    return {padded[start : start + QGRAM_SIZE] for start in range(len(padded) - QGRAM_SIZE + 1)}


class TrigramIndex:
    """Chỉ mục ngược trigram → vị trí từ khóa trong từ điển."""

    __slots__ = ("_postings", "_keywords")

    def __init__(self, keywords: Sequence[str]) -> None:
        postings: dict[str, list[int]] = defaultdict(list)
        for index, keyword in enumerate(keywords):
            padded = _PADDING + keyword + _PADDING
            for gram in {
                padded[start : start + QGRAM_SIZE] for start in range(len(padded) - QGRAM_SIZE + 1)
            }:
                postings[gram].append(index)
        self._postings: dict[str, list[int]] = dict(postings)
        self._keywords: Sequence[str] = keywords

    def candidates(self, query: str, max_distance: int) -> list[str] | None:
        """Ứng viên có thể có khoảng cách ``<= max_distance`` tới ``query``.

        Trả về ``None`` khi bộ lọc không còn khả năng loại bỏ (bên gọi phải
        tự quét đầy đủ).
        """
        grams = qgrams(query)
        min_shared = len(grams) - QGRAM_SIZE * max_distance
        if min_shared <= 0:
            return None

        counts: dict[int, int] = {}
        postings = self._postings
        for gram in grams:
            posting = postings.get(gram)
            if posting is None:
                continue
            for index in posting:
                counts[index] = counts.get(index, 0) + 1

        keywords = self._keywords
        query_length = len(query)
        return [
            keywords[index]
            for index, shared in counts.items()
            if shared >= min_shared and abs(len(keywords[index]) - query_length) <= max_distance
        ]
