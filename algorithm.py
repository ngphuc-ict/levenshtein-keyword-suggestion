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

    @staticmethod
    def fold_accents(text: str) -> str:
        """Bỏ dấu tiếng Việt (đ -> d) để gõ thiếu dấu vẫn khớp."""
        decomposed = unicodedata.normalize("NFD", text)
        stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
        return stripped.replace("đ", "d")

    @staticmethod
    def prefix_distance(query: str, keyword: str) -> int:
        """Khoảng cách nhỏ nhất từ query tới một *tiền tố* của keyword.

        Dùng cùng bảng quy hoạch động như levenshtein_distance, nhưng thay vì
        lấy ô cuối cùng D[m][n] ta lấy min D[m][j] trên hàng cuối (j = 0..n).
        Nhờ vậy truy vấn đang gõ dở như "điện tho" khớp với "điện thoại ...".
        """
        previous = list(range(len(keyword) + 1))
        for row, query_char in enumerate(query, start=1):
            current = [row]
            for column, keyword_char in enumerate(keyword, start=1):
                current.append(
                    min(
                        current[column - 1] + 1,
                        previous[column] + 1,
                        previous[column - 1] + (query_char != keyword_char),
                    )
                )
            previous = current
        return min(previous)

    @staticmethod
    def starts_a_word(query: str, keyword: str) -> bool:
        """True nếu query xuất hiện ở đầu một từ của keyword."""
        return (" " + query) in (" " + keyword)

    def rank_suggestions(
        self,
        query: str,
        dictionary: Iterable[str],
        limit: int = 5,
    ) -> List[Suggestion]:
        """Trả về tối đa limit gợi ý gần nhất, cùng khoảng cách chỉnh sửa.

        distance là khoảng cách từ truy vấn tới tiền tố gần nhất của từ khóa.
        Khoảng cách tính trên chuỗi đã bỏ dấu. Thứ tự xếp hạng: (distance,
        không bắt đầu một từ trùng truy vấn, khoảng cách tiền tố có dấu,
        khoảng cách toàn chuỗi, chữ cái) nên kết quả không phụ thuộc thứ tự
        duyệt của set hoặc nguồn từ điển. Từ khóa trùng sau chuẩn hóa chỉ
        được tính một lần.
        """
        if limit <= 0 or not isinstance(query, str):
            return []
        normalized_query = self.normalize(query)
        if not normalized_query or dictionary is None:
            return []

        folded_query = self.fold_accents(normalized_query)
        seen = set()
        scored = []
        for entry in dictionary:
            candidate = self.normalize(entry) if isinstance(entry, str) else ""
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            folded = self.fold_accents(candidate)
            scored.append(
                (
                    self.prefix_distance(folded_query, folded),
                    not self.starts_a_word(folded_query, folded),
                    self.prefix_distance(normalized_query, candidate),
                    self.levenshtein_distance(normalized_query, candidate),
                    candidate,
                )
            )

        return [
            Suggestion(keyword=item[-1], distance=item[0])
            for item in heapq.nsmallest(limit, scored)
        ]

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
