"""Bộ gợi ý từ khóa: xếp hạng top-k theo khoảng cách Levenshtein.

Quy trình cho mỗi truy vấn:

1. **Sinh ứng viên bằng trigram** (``index.TrigramIndex``): loại bỏ những từ
   khóa chắc chắn xa hơn ngưỡng, kèm chứng minh không bỏ sót ứng viên.
2. **Tính khoảng cách có chặn** (``bounded_levenshtein_distance``): chỉ cần
   biết khoảng cách có vượt ngưỡng hay không, nên dùng bản dải chéo
   ``O(len * ngưỡng)`` thay vì ``O(len^2)``.
3. **Nới ngưỡng dần** 1, 2, 4, ... cho tới khi gom đủ ``k`` kết quả. Khi đã
   đủ, mọi từ khóa có khoảng cách ``<=`` ngưỡng đều nằm trong tập ứng viên,
   nên top-k thu được là *chính xác*, không phải gần đúng.
4. Nếu bộ lọc trigram hết tác dụng (truy vấn quá ngắn hoặc quá xa từ điển),
   chuyển sang quét theo nhóm độ dài — chậm hơn nhưng vẫn đúng.

Xếp hạng giống hệt ``algorithm.py`` của repo: theo ``(distance, keyword)``
tăng dần, mỗi từ khóa chỉ tính một lần. Nhờ vậy kết quả backend trùng khớp
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
from .index import TrigramIndex
from .levenshtein import bounded_levenshtein_distance, levenshtein_distance
from .text import normalize_text


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

    __slots__ = ("_dictionary", "_index", "_cache")

    def __init__(self, dictionary: KeywordDictionary, cache_size: int = 1024) -> None:
        self._dictionary = dictionary
        self._index = TrigramIndex(dictionary.keywords)
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
        """Trả về top-k chính xác và số lần tính khoảng cách."""
        distance_cap = max_distance
        threshold = 1

        while True:
            cutoff = threshold if distance_cap is None else min(threshold, distance_cap)
            candidates = self._index.candidates(query, cutoff)

            if candidates is None:
                # Bộ lọc trigram không còn tác dụng: quét đầy đủ theo độ dài.
                return self._scan_by_length(query, limit, distance_cap)

            scored: list[tuple[int, str]] = []
            for keyword in candidates:
                distance = bounded_levenshtein_distance(query, keyword, cutoff)
                if distance <= cutoff:
                    scored.append((distance, keyword))

            if len(scored) >= limit:
                scored.sort()
                return (
                    tuple(
                        Suggestion(keyword=keyword, distance=distance)
                        for distance, keyword in scored[:limit]
                    ),
                    len(candidates),
                )

            if distance_cap is not None and cutoff >= distance_cap:
                # Đã chạm trần max_distance: trả về những gì tìm được.
                scored.sort()
                return (
                    tuple(
                        Suggestion(keyword=keyword, distance=distance)
                        for distance, keyword in scored
                    ),
                    len(candidates),
                )

            # Tăng dần từng đơn vị: ngưỡng càng sát khoảng cách thật thì
            # tập ứng viên càng nhỏ, đổi lại thêm vài lượt sinh ứng viên rẻ.
            threshold += 1

    def _scan_by_length(
        self,
        query: str,
        limit: int,
        max_distance: int | None,
    ) -> tuple[tuple[Suggestion, ...], int]:
        """Quét từ khóa theo chênh lệch độ dài tăng dần (đường dự phòng).

        Với mọi chuỗi, ``distance >= |len(a) - len(b)|``. Khi đã có đủ
        ``limit`` gợi ý và khoảng cách tệ nhất là ``d``, mọi nhóm lệch độ dài
        hơn ``d`` bị bỏ qua. Đây cũng là lý do đường dự phòng vẫn nhanh với
        truy vấn ngắn.
        """
        by_length = self._dictionary.by_length
        lengths = self._dictionary.lengths
        query_length = len(query)

        best: list[tuple[int, str]] = []
        evaluated = 0
        threshold: int | None = max_distance
        max_offset = max(lengths[-1] - query_length, query_length - lengths[0])
        offset = 0

        while offset <= max_offset:
            if threshold is not None and offset > threshold:
                break

            if offset == 0:
                candidate_lengths = (query_length,)
            else:
                candidate_lengths = (query_length - offset, query_length + offset)

            for length in candidate_lengths:
                bucket = by_length.get(length)
                if not bucket:
                    continue
                for keyword in bucket:
                    evaluated += 1

                    if threshold is None:
                        distance = levenshtein_distance(query, keyword)
                    else:
                        distance = bounded_levenshtein_distance(query, keyword, threshold)
                        if distance > threshold:
                            continue
                        if len(best) >= limit and (distance, keyword) >= best[-1]:
                            continue

                    insort(best, (distance, keyword))
                    if len(best) > limit:
                        best.pop()

                    if len(best) >= limit:
                        threshold = best[-1][0]
                        if max_distance is not None:
                            threshold = min(threshold, max_distance)

            offset += 1

        return (
            tuple(Suggestion(keyword=keyword, distance=distance) for distance, keyword in best),
            evaluated,
        )
