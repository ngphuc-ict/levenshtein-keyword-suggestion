"""Nạp và lập chỉ mục từ điển từ khóa."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from .text import normalize_text


@dataclass(frozen=True, slots=True)
class DictionaryStats:
    """Thống kê mô tả từ điển, phục vụ endpoint ``/stats``."""

    size: int
    min_length: int
    max_length: int
    average_length: float
    distinct_lengths: int
    source: str
    load_ms: float


class EmptyDictionaryError(ValueError):
    """Từ điển rỗng sau khi chuẩn hóa."""


class KeywordDictionary:
    """Tập từ khóa đã chuẩn hóa, kèm chỉ mục theo độ dài.

    Chỉ mục ``by_length`` giúp bộ gợi ý duyệt các từ khóa theo thứ tự chênh
    lệch độ dài tăng dần. Vì khoảng cách Levenshtein luôn lớn hơn hoặc bằng
    chênh lệch độ dài, khi đã có đủ ``limit`` gợi ý với khoảng cách ``d`` thì
    mọi từ khóa lệch độ dài hơn ``d`` đều không thể lọt vào top — nhờ đó cắt
    được phần lớn khối lượng tính toán.
    """

    __slots__ = ("keywords", "by_length", "lengths", "_stats")

    def __init__(
        self,
        keywords: object,
        *,
        source: str = "<memory>",
        load_ms: float = 0.0,
    ) -> None:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in keywords:  # type: ignore[union-attr]
            keyword = normalize_text(raw)
            if keyword and keyword not in seen:
                seen.add(keyword)
                normalized.append(keyword)

        if not normalized:
            raise EmptyDictionaryError(
                "Từ điển rỗng sau khi chuẩn hóa, không thể khởi động dịch vụ."
            )

        normalized.sort()
        self.keywords: tuple[str, ...] = tuple(normalized)

        grouped: dict[int, list[str]] = defaultdict(list)
        for keyword in normalized:
            grouped[len(keyword)].append(keyword)
        self.by_length: dict[int, tuple[str, ...]] = {
            length: tuple(words) for length, words in grouped.items()
        }
        self.lengths: tuple[int, ...] = tuple(sorted(self.by_length))

        total_characters = sum(len(keyword) for keyword in normalized)
        self._stats = DictionaryStats(
            size=len(normalized),
            min_length=self.lengths[0],
            max_length=self.lengths[-1],
            average_length=round(total_characters / len(normalized), 2),
            distinct_lengths=len(self.lengths),
            source=source,
            load_ms=round(load_ms, 3),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> KeywordDictionary:
        """Đọc từ điển UTF-8, mỗi dòng một từ khóa.

        Khác với bản demo cũ (in lỗi rồi trả danh sách rỗng), backend dừng
        ngay khi thiếu tệp để lỗi cấu hình hiện ra lúc khởi động thay vì
        âm thầm trả về gợi ý rỗng.
        """
        dictionary_path = Path(path)
        started = perf_counter()
        if not dictionary_path.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy tệp từ điển: {dictionary_path}. "
                "Đặt biến môi trường DICTIONARY_PATH trỏ tới tệp dictionary.txt."
            )

        with dictionary_path.open("r", encoding="utf-8") as stream:
            lines = stream.readlines()

        return cls(
            lines,
            source=str(dictionary_path),
            load_ms=(perf_counter() - started) * 1000,
        )

    @property
    def stats(self) -> DictionaryStats:
        return self._stats

    def __len__(self) -> int:
        return len(self.keywords)
