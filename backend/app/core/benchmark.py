"""Chạy và lưu kết quả đo hiệu năng qua API (``/benchmark/runs``).

Module giữ ba việc:

* ``naive_top_k`` — bản quét toàn bộ từ điển, tương đương cách làm trong
  ``algorithm.py`` của repo, dùng làm mốc so sánh.
* ``run_benchmark`` — đo từng truy vấn bằng bộ gợi ý đã tối ưu, tùy chọn đo
  kèm mốc quét toàn bộ và đối chiếu top-k của hai bên.
* ``BenchmarkStore`` — kho lưu kết quả trong bộ nhớ (tối đa 20 lần chạy) để
  endpoint tra cứu và xuất CSV.
"""

from __future__ import annotations

import csv
import io
import statistics
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass

from .dictionary import KeywordDictionary
from .levenshtein import levenshtein_distance
from .suggester import KeywordSuggester
from .text import normalize_text

DEFAULT_QUERIES: tuple[str, ...] = (
    "điện thoại samsng",
    "tai nghe blutooth",
    "áo thun akko",
    "laptop dell i5",
    "bàn phím cơ",
)

STORE_CAPACITY = 20


@dataclass(frozen=True, slots=True)
class QueryMeasurement:
    """Kết quả một truy vấn trong một lần chạy benchmark."""

    query: str
    normalized_query: str
    took_ms: float
    candidates: int
    suggestions: tuple[tuple[str, int], ...]
    baseline_ms: float | None = None
    baseline_suggestions: tuple[tuple[str, int], ...] = ()
    matches_baseline: bool | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkRun:
    """Một lần chạy benchmark hoàn chỉnh."""

    run_id: str
    status: str
    created_at: float
    duration_ms: float
    limit: int
    repeats: int
    include_baseline: bool
    measurements: tuple[QueryMeasurement, ...]
    summary: dict[str, float | int | None]


def naive_top_k(
    dictionary: KeywordDictionary,
    query: str,
    limit: int,
) -> tuple[tuple[str, int], ...]:
    """Top-k theo cách quét toàn bộ từ điển (giống ``algorithm.py``).

    Đây là mốc so sánh: tính khoảng cách cho mọi từ khóa rồi sắp theo
    ``(distance, keyword)``. Chậm hơn nhiều nhưng là bản gốc của nhóm.
    """
    normalized = normalize_text(query)
    scored = [
        (levenshtein_distance(normalized, keyword), keyword) for keyword in dictionary.keywords
    ]
    scored.sort(key=lambda item: (item[0], item[1]))
    return tuple((keyword, distance) for distance, keyword in scored[:limit])


def _percentile(values: list[float], fraction: float) -> float:
    if not values:  # pragma: no cover - danh sách truy vấn luôn có ít nhất 1 phần tử
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def run_benchmark(
    suggester: KeywordSuggester,
    dictionary: KeywordDictionary,
    queries: list[str],
    *,
    limit: int = 5,
    repeats: int = 1,
    include_baseline: bool = False,
) -> BenchmarkRun:
    """Đo hiệu năng cho từng truy vấn và tổng hợp thành một ``BenchmarkRun``.

    Với ``repeats > 1``, mỗi truy vấn chạy nhiều lần và lấy lần nhanh nhất —
    cách đo này giảm ảnh hưởng của nhiễu hệ thống. Bộ đệm được xóa trước mỗi
    lần đo để kết quả phản ánh chi phí thật của thuật toán.
    """
    started = time.perf_counter()
    measurements: list[QueryMeasurement] = []

    for raw_query in queries:
        normalized = normalize_text(raw_query)
        best: QueryMeasurement | None = None

        for _ in range(max(1, repeats)):
            # Đo nguội: xóa bộ đệm trước mỗi lần đo để không vô tình ghi nhận
            # một lần trúng cache (0 ms) thành hiệu năng thật của thuật toán.
            suggester.clear_cache()
            result = suggester.suggest(raw_query, limit=limit)
            suggestions = tuple((item.keyword, item.distance) for item in result.suggestions)
            measurement = QueryMeasurement(
                query=raw_query,
                normalized_query=normalized,
                took_ms=round(result.took_ms, 3),
                candidates=result.evaluated,
                suggestions=suggestions,
            )
            if best is None or measurement.took_ms < best.took_ms:
                best = measurement

        assert best is not None  # repeats >= 1 nên vòng lặp luôn chạy
        if include_baseline:
            baseline_started = time.perf_counter()
            baseline = naive_top_k(dictionary, raw_query, limit)
            baseline_ms = (time.perf_counter() - baseline_started) * 1000
            best = QueryMeasurement(
                query=best.query,
                normalized_query=best.normalized_query,
                took_ms=best.took_ms,
                candidates=best.candidates,
                suggestions=best.suggestions,
                baseline_ms=round(baseline_ms, 3),
                baseline_suggestions=baseline,
                matches_baseline=baseline == best.suggestions,
            )

        measurements.append(best)

    duration_ms = (time.perf_counter() - started) * 1000
    times = [item.took_ms for item in measurements]
    baseline_times = [item.baseline_ms for item in measurements if item.baseline_ms is not None]

    summary: dict[str, float | int | None] = {
        "query_count": len(measurements),
        "mean_ms": round(statistics.fmean(times), 3) if times else 0.0,
        "p50_ms": round(statistics.median(times), 3) if times else 0.0,
        "p95_ms": round(_percentile(times, 0.95), 3),
        "min_ms": round(min(times), 3) if times else 0.0,
        "max_ms": round(max(times), 3) if times else 0.0,
        "total_candidates": sum(item.candidates for item in measurements),
        "baseline_mean_ms": (
            round(statistics.fmean(baseline_times), 3) if baseline_times else None
        ),
        "speedup_vs_baseline": (
            round(statistics.fmean(baseline_times) / statistics.fmean(times), 3)
            if baseline_times and times and statistics.fmean(times) > 0
            else None
        ),
        "baseline_mismatches": sum(1 for item in measurements if item.matches_baseline is False),
    }

    return BenchmarkRun(
        run_id=uuid.uuid4().hex[:12],
        status="completed",
        created_at=time.time(),
        duration_ms=round(duration_ms, 3),
        limit=limit,
        repeats=max(1, repeats),
        include_baseline=include_baseline,
        measurements=tuple(measurements),
        summary=summary,
    )


class BenchmarkStore:
    """Kho lưu kết quả benchmark trong bộ nhớ, an toàn luồng.

    Chỉ giữ 20 lần chạy gần nhất để dịch vụ demo không phình bộ nhớ; lần cũ
    nhất bị loại khi vượt sức chứa.
    """

    __slots__ = ("_runs", "_order", "_lock", "capacity")

    def __init__(self, capacity: int = STORE_CAPACITY) -> None:
        self._runs: OrderedDict[str, BenchmarkRun] = OrderedDict()
        self._order: list[str] = []
        self._lock = threading.Lock()
        self.capacity = max(1, capacity)

    def add(self, run: BenchmarkRun) -> None:
        with self._lock:
            self._runs[run.run_id] = run
            self._order.append(run.run_id)
            while len(self._order) > self.capacity:
                oldest = self._order.pop(0)
                self._runs.pop(oldest, None)

    def get(self, run_id: str) -> BenchmarkRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def ids(self) -> list[str]:
        with self._lock:
            return list(self._order)

    def __len__(self) -> int:
        with self._lock:
            return len(self._runs)


def run_to_csv(run: BenchmarkRun) -> str:
    """Kết xuất kết quả một lần chạy ra CSV (mỗi dòng một gợi ý)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "run_id",
            "query",
            "rank",
            "keyword",
            "distance",
            "took_ms",
            "candidates",
            "baseline_ms",
            "matches_baseline",
        ]
    )
    for measurement in run.measurements:
        for rank, (keyword, distance) in enumerate(measurement.suggestions, start=1):
            writer.writerow(
                [
                    run.run_id,
                    measurement.query,
                    rank,
                    keyword,
                    distance,
                    f"{measurement.took_ms:.3f}",
                    measurement.candidates,
                    "" if measurement.baseline_ms is None else f"{measurement.baseline_ms:.3f}",
                    "" if measurement.matches_baseline is None else measurement.matches_baseline,
                ]
            )
    return buffer.getvalue()
