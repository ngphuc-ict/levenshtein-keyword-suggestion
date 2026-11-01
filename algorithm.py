"""Gợi ý từ khóa bằng khoảng cách Levenshtein và quy hoạch động.

Ví dụ:
    from data_processor import DictionaryProcessor
    from algorithm import LevenshteinSuggester

    dictionary = DictionaryProcessor("dictionary.txt").load_data()
    suggester = LevenshteinSuggester()
    suggestions = suggester.rank_suggestions("dien thoai samsng", dictionary)
    for item in suggestions:
        print(item.keyword, item.distance)
"""

from dataclasses import dataclass
import heapq
import re
import unicodedata
from typing import Iterable, List


@dataclass(frozen=True)
class Suggestion:
    """Một từ khóa gợi ý cùng số phép chỉnh sửa cần thiết."""

    keyword: str
    distance: int


class LevenshteinSuggester:
    """Tính khoảng cách chỉnh sửa và tìm các từ khóa gần nhất trong từ điển."""

    @staticmethod
    def normalize(text: str) -> str:
        """Chuẩn hóa giống DictionaryProcessor: NFC, chữ thường, bỏ dấu câu."""
        if not isinstance(text, str) or not text:
            return ""
        text = unicodedata.normalize("NFC", text).lower()
        text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def levenshtein_distance(source: str, target: str) -> int:
        """Số phép chèn, xóa, thay thế tối thiểu; mỗi phép có chi phí 1.

        Quy hoạch động với hai hàng có thời gian O(m*n), bộ nhớ O(min(m,n)).
        Chuỗi Unicode tiếng Việt được xử lý theo ký tự Unicode.
        """
        if source == target:
            return 0
        if not source:
            return len(target)
        if not target:
            return len(source)

        # Giữ chuỗi ngắn hơn làm cột để giảm bộ nhớ.
        if len(source) < len(target):
            source, target = target, source

        previous = list(range(len(target) + 1))
        for row, source_char in enumerate(source, start=1):
            current = [row]
            for column, target_char in enumerate(target, start=1):
                insertion = current[column - 1] + 1
                deletion = previous[column] + 1
                substitution = previous[column - 1] + (source_char != target_char)
                current.append(min(insertion, deletion, substitution))
            previous = current
        return previous[-1]

    def rank_suggestions(
        self,
        query: str,
        dictionary: Iterable[str],
        limit: int = 5,
    ) -> List[Suggestion]:
        """Trả về tối đa limit gợi ý gần nhất, cùng khoảng cách chỉnh sửa.

        Khi khoảng cách bằng nhau, xếp theo chữ cái để kết quả không phụ
        thuộc thứ tự duyệt của set hoặc nguồn từ điển. Từ khóa trùng sau
        chuẩn hóa chỉ được tính một lần.
        """
        if limit <= 0 or not isinstance(query, str):
            return []
        normalized_query = self.normalize(query)
        if not normalized_query or dictionary is None:
            return []

        seen = set()
        scored = []
        for entry in dictionary:
            candidate = self.normalize(entry) if isinstance(entry, str) else ""
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            scored.append(
                Suggestion(
                    keyword=candidate,
                    distance=self.levenshtein_distance(normalized_query, candidate),
                )
            )

        return heapq.nsmallest(
            limit, scored, key=lambda item: (item.distance, item.keyword)
        )

    def suggest(
        self,
        query: str,
        dictionary: Iterable[str],
        limit: int = 5,
    ) -> List[str]:
        """Trả về danh sách từ khóa gợi ý không kèm khoảng cách."""
        return [
            item.keyword
            for item in self.rank_suggestions(query, dictionary, limit)
        ]
