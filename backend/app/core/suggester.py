"""Bộ gợi ý từ khóa: xếp hạng top-k theo khoảng cách Levenshtein.

``distance`` là khoảng cách từ truy vấn tới *tiền tố* gần nhất của từ khóa,
tính trên chuỗi đã bỏ dấu, để truy vấn đang gõ dở hoặc thiếu dấu vẫn có gợi ý.

Quy trình cho mỗi truy vấn:

1. **Duyệt trie** (``trie.PrefixTrie``): các từ khóa chung tiền tố dùng chung
   cột quy hoạch động, cắt cả nhánh khi cột vượt ngưỡng (chính xác, không gần đúng).
2. **Nới ngưỡng dần** 1, 2, 3, 6, ... cho tới khi gom đủ ``k`` kết quả. Khi đã
   đủ, mọi từ khóa có khoảng cách ``<=`` ngưỡng đều đã được tìm thấy nên top-k
   là chính xác.
3. **Phân hạng khi bằng điểm** trên chuỗi *có dấu* để từ có dấu đúng lên trước.

Xếp hạng giống hệt ``algorithm.py`` của repo: theo ``(tiền tố không dấu,
không bắt đầu một từ trùng truy vấn, tiền tố có dấu, toàn chuỗi,
keyword)``. Nhờ vậy kết quả backend trùng khớp
với bản thuật toán nhóm đã viết.
"""

from __future__ import annotations

import threading
import time
from bisect import insort
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from .dictionary import KeywordDictionary
from .levenshtein import levenshtein_distance, prefix_levenshtein_distance
from .text import fold_accents, normalize_text, starts_a_word
from .trie import PrefixTrie


@dataclass(frozen=True, slots=True)
class Suggestion:
    """Một từ khóa gợi ý kèm số phép chỉnh sửa."""

    keyword: str
    distance: int


@dataclass(frozen=True, slots=True)
class SuggestResult:
    """Kết quả một lần gợi ý, kèm số liệu đo để hiển thị/báo cáo."""

    query: str
    normalized_query: str
    suggestions: tuple[Suggestion, ...]
    took_ms: float
    cached: bool
    evaluated: int


class _LRUCache:
    """LRU nhỏ, an toàn luồng, có đếm hit/miss cho endpoint ``/stats``."""

    __slots__ = ("_capacity", "_data", "_lock", "hits", "misses", "evictions")

    def __init__(self, capacity: int) -> None:
        self._capacity = max(0, int(capacity))
        self._data: OrderedDict[Any, Any] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: Any) -> Any | None:
        if self._capacity == 0:
            return None
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self.hits += 1
                return self._data[key]
            self.misses += 1
            return None

    def put(self, key: Any, value: Any) -> None:
        if self._capacity == 0:
            return
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self._capacity:
                self._data.popitem(last=False)
                self.evictions += 1

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def stats(self) -> dict[str, float | int]:
        with self._lock:
            total = self.hits + self.misses
            return {
                "capacity": self._capacity,
                "size": len(self._data),
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": round(self.hits / total, 4) if total else 0.0,
            }


class KeywordSuggester:
    """Tìm tối đa ``limit`` từ khóa gần truy vấn nhất."""

    __slots__ = ("_dictionary", "_folded", "_trie", "_cache")

    def __init__(self, dictionary: KeywordDictionary, cache_size: int = 1024) -> None:
        self._dictionary = dictionary
        self._folded = [fold_accents(keyword) for keyword in dictionary.keywords]
        self._trie = PrefixTrie(self._folded)
        self._cache = _LRUCache(cache_size)

    @property
    def dictionary(self) -> KeywordDictionary:
        return self._dictionary

    def suggest(
        self,
        query: str,
        limit: int = 5,
        max_distance: int | None = None,
    ) -> SuggestResult:
        """Trả về tối đa ``limit`` gợi ý cho ``query``.

        ``max_distance`` (tùy chọn) giới hạn khoảng cách tối đa được chấp
        nhận; khi đó có thể trả về ít hơn ``limit`` phần tử, thậm chí rỗng.
        """
        started = time.perf_counter()
        normalized = normalize_text(query)
        raw_query = query if isinstance(query, str) else ""

        if not normalized or limit <= 0:
            return SuggestResult(
                query=raw_query,
                normalized_query=normalized,
                suggestions=(),
                took_ms=round((time.perf_counter() - started) * 1000, 3),
                cached=False,
                evaluated=0,
            )

        cache_key = (normalized, limit, max_distance)
        cached_value = self._cache.get(cache_key)
        if cached_value is not None:
            return SuggestResult(
                query=raw_query,
                normalized_query=normalized,
                suggestions=cached_value,
                took_ms=round((time.perf_counter() - started) * 1000, 3),
                cached=True,
                evaluated=0,
            )

        ranked, evaluated = self._rank(normalized, limit, max_distance)
        self._cache.put(cache_key, ranked)

        return SuggestResult(
            query=raw_query,
            normalized_query=normalized,
            suggestions=ranked,
            took_ms=round((time.perf_counter() - started) * 1000, 3),
            cached=False,
            evaluated=evaluated,
        )

    def cache_stats(self) -> dict[str, float | int]:
        return self._cache.stats()

    def clear_cache(self) -> None:
        self._cache.clear()

    def _rank(
        self,
        query: str,
        limit: int,
        max_distance: int | None,
    ) -> tuple[tuple[Suggestion, ...], int]:
        """Trả về top-k chính xác và số từ khóa đã đạt ngưỡng."""
        folded_query = fold_accents(query)
        threshold = 1

        while True:
            cutoff = threshold if max_distance is None else min(threshold, max_distance)
            found = self._trie.search(folded_query, cutoff)

            # Khoảng cách tiền tố luôn <= len(query), nên chạm mức đó là đã xét hết.
            exhausted = cutoff >= len(query)
            capped = max_distance is not None and cutoff >= max_distance
            if len(found) >= limit or exhausted or capped:
                return self._order(query, folded_query, found, limit), len(found)

            threshold = threshold + 1 if threshold < 3 else threshold * 2

    def _order(
        self,
        query: str,
        folded_query: str,
        found: dict[int, int],
        limit: int,
    ) -> tuple[Suggestion, ...]:
        """Xếp theo (tiền tố không dấu, không bắt đầu một từ, rồi chọn theo dấu/toàn chuỗi)."""
        keywords = self._dictionary.keywords
        groups: dict[tuple[int, bool], list[str]] = {}
        for word_id, distance in found.items():
            key = (distance, not starts_a_word(folded_query, self._folded[word_id]))
            groups.setdefault(key, []).append(keywords[word_id])

        result: list[Suggestion] = []
        for key in sorted(groups):
            need = limit - len(result)
            if need <= 0:
                break
            for keyword in _select_with_accents(query, groups[key], need):
                result.append(Suggestion(keyword=keyword, distance=key[0]))
        return tuple(result)


def _select_with_accents(query: str, keywords: list[str], need: int) -> list[str]:
    """``need`` từ khóa tốt nhất theo (tiền tố có dấu, toàn chuỗi, chữ cái)."""
    bound = len(query)
    top: list[int] = []
    scored: list[tuple[int, str]] = []
    for keyword in keywords:
        distance = prefix_levenshtein_distance(query, keyword, bound)
        if distance > bound:
            continue
        scored.append((distance, keyword))
        insort(top, distance)
        if len(top) > need:
            top.pop()
        if len(top) >= need:
            bound = top[-1]

    levels: dict[int, list[str]] = {}
    for distance, keyword in scored:
        if distance <= top[-1]:
            levels.setdefault(distance, []).append(keyword)

    result: list[str] = []
    for distance in sorted(levels):
        remaining = need - len(result)
        if remaining <= 0:
            break
        result.extend(_best_by_full_distance(query, levels[distance], remaining))
    return result


def _best_by_full_distance(query: str, keywords: list[str], need: int) -> list[str]:
    """``need`` từ khóa có (khoảng cách toàn chuỗi, chữ cái) nhỏ nhất.

    ``distance >= |len(a) - len(b)|`` nên duyệt theo chênh lệch độ dài tăng
    dần và dừng ngay khi cận dưới đã vượt khoảng cách tệ nhất đang giữ,
    tránh tính DP đầy đủ cho cả nhóm lớn.
    """
    query_length = len(query)
    ordered = sorted(keywords, key=lambda keyword: (abs(len(keyword) - query_length), keyword))
    best: list[tuple[int, str]] = []
    for keyword in ordered:
        if len(best) >= need and abs(len(keyword) - query_length) > best[-1][0]:
            break
        insort(best, (levenshtein_distance(query, keyword), keyword))
        if len(best) > need:
            best.pop()
    return [keyword for _, keyword in best]
