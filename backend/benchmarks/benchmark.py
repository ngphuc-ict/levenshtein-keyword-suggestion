#!/usr/bin/env python3
"""Đo hiệu năng backend so với bản thuật toán gốc trên cùng từ điển.

Cách chạy (trong thư mục backend, đã cài requirements)::

    python benchmarks/benchmark.py
    python benchmarks/benchmark.py --queries 30 --naive 8 --json ket-qua.json

Script cũng kiểm tra chéo: với những truy vấn chạy cả hai bản, top-5 phải
trùng khớp tuyệt đối (từ khóa và khoảng cách).
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
for _path in (str(BACKEND_DIR), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from algorithm import LevenshteinSuggester  # noqa: E402  (bản gốc của repo)

from app.core.dictionary import KeywordDictionary  # noqa: E402
from app.core.suggester import KeywordSuggester  # noqa: E402

ALPHABET = "abcđeêghiklmnôơpqrstuưvxyáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọ"

FIXED_QUERIES = [
    "điện thoại samsng",
    "tai nghe blutooth",
    "áo thun akko",
    "laptop dell i5",
    "bàn phím cơ",
]


def mutate(word: str, rng: random.Random) -> str:
    characters = list(word)
    for _ in range(rng.randint(1, 3)):
        if not characters:
            break
        operation = rng.choice("ids")
        index = rng.randrange(len(characters))
        if operation == "i":
            characters.insert(index, rng.choice(ALPHABET))
        elif operation == "d":
            characters.pop(index)
        else:
            characters[index] = rng.choice(ALPHABET)
    return "".join(characters)


def build_queries(keywords: list[str], count: int, rng: random.Random) -> list[str]:
    queries = list(FIXED_QUERIES)
    while len(queries) < count:
        queries.append(mutate(rng.choice(keywords), rng))
    return queries[:count]


def measure(function) -> tuple[float, object]:
    started = time.perf_counter()
    result = function()
    return (time.perf_counter() - started) * 1000, result


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark backend gợi ý từ khóa")
    parser.add_argument(
        "--dictionary",
        default=str(REPO_ROOT / "dictionary.txt"),
        help="Đường dẫn dictionary.txt",
    )
    parser.add_argument("--queries", type=int, default=20, help="Số truy vấn đo bản tối ưu")
    parser.add_argument(
        "--naive",
        type=int,
        default=5,
        help="Số truy vấn đo bản gốc (bản gốc chậm nên chỉ đo một phần)",
    )
    parser.add_argument("--limit", type=int, default=5, help="Số gợi ý mỗi truy vấn")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--worst-case",
        default="nồi cơm điện tử",
        help="Truy vấn cố tình xa từ điển, đo riêng khỏi thống kê chính",
    )
    parser.add_argument("--json", dest="json_path", default=None, help="Ghi kết quả ra JSON")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    load_ms, dictionary = measure(lambda: KeywordDictionary.from_file(args.dictionary))
    build_ms, suggester = measure(lambda: KeywordSuggester(dictionary, cache_size=256))

    print(f"Từ điển : {len(dictionary):,} từ khóa".replace(",", "."))
    print(f"Nạp     : {load_ms:.1f} ms")
    print(f"Chỉ mục : {build_ms:.1f} ms (trigram + sắp xếp theo độ dài)")
    print()

    queries = build_queries(list(dictionary.keywords), args.queries, rng)
    optimized: list[dict[str, object]] = []
    times: list[float] = []

    for query in queries:
        suggester.clear_cache()  # đo "nguội", không ăn cache
        elapsed, result = measure(lambda q=query: suggester.suggest(q, limit=args.limit))
        times.append(elapsed)
        optimized.append(
            {
                "query": query,
                "ms": round(elapsed, 3),
                "evaluated": result.evaluated,
                "suggestions": [(item.keyword, item.distance) for item in result.suggestions],
            }
        )

    # Bản gốc: quét toàn bộ từ điển, chuẩn hóa lại từng từ khóa mỗi truy vấn.
    reference = LevenshteinSuggester()
    naive_keywords = list(dictionary.keywords)
    naive_sample = optimized[: max(0, min(args.naive, len(optimized)))]

    mismatches = 0
    naive_times: list[float] = []
    for row in naive_sample:
        elapsed, result = measure(
            lambda q=row["query"]: reference.rank_suggestions(q, naive_keywords, limit=args.limit)
        )
        naive_times.append(elapsed)
        reference_top = [(item.keyword, item.distance) for item in result]
        row["naive_ms"] = round(elapsed, 3)
        row["speedup"] = round(elapsed / row["ms"], 1) if row["ms"] else 0.0
        if reference_top != row["suggestions"]:
            mismatches += 1
            row["mismatch"] = {"expected": reference_top, "actual": row["suggestions"]}

    print(f"{'Truy vấn':<34}{'Tối ưu':>10}{'Gốc':>11}{'Nhanh hơn':>11}{'Ứng viên':>10}")
    print("-" * 76)
    for row in optimized:
        query = row["query"]
        shown = query if len(query) <= 32 else query[:29] + "..."
        naive_ms = f"{row['naive_ms']:.1f}" if "naive_ms" in row else "-"
        speedup = f"x{row['speedup']}" if "speedup" in row else "-"
        evaluated = f"{row['evaluated']:,}".replace(",", ".")
        print(f"{shown:<34}{row['ms']:>9.2f}ms{naive_ms:>10}{speedup:>11}{evaluated:>10}")

    print()
    print(
        f"Tối ưu (nguội, {len(times)} truy vấn): "
        f"trung bình {statistics.fmean(times):.2f} ms | "
        f"p50 {percentile(times, 0.5):.2f} ms | "
        f"p95 {percentile(times, 0.95):.2f} ms | "
        f"min {min(times):.2f} ms | max {max(times):.2f} ms"
    )

    # Truy vấn không có từ khóa nào gần trong từ điển: bộ lọc trigram hết tác
    # dụng nên phải quét đầy đủ. Đo riêng để không làm sai lệch thống kê trên.
    suggester.clear_cache()
    worst_ms, worst_result = measure(lambda: suggester.suggest(args.worst_case, limit=args.limit))
    worst_evaluated = f"{worst_result.evaluated:,}".replace(",", ".")
    print(
        f"Xa từ điển ({args.worst_case}): {worst_ms:.0f} ms, "
        f"{worst_evaluated} từ khóa đã tính (quét đầy đủ, vẫn đúng)"
    )

    warm_query = queries[0]
    measure(lambda: suggester.suggest(warm_query, limit=args.limit))
    warm_ms, _ = measure(lambda: suggester.suggest(warm_query, limit=args.limit))
    print(f"Bộ đệm (cache hit)      : {warm_ms:.3f} ms")

    if naive_times:
        naive_average = statistics.fmean(naive_times)
        print(
            f"Bản gốc (quét toàn bộ)  : trung bình {naive_average:.1f} ms "
            f"→ nhanh hơn khoảng x{naive_average / statistics.fmean(times):.1f} lần"
        )

    if mismatches:
        print(f"\n[LỖI] {mismatches} truy vấn cho kết quả khác bản gốc!")
        return 1

    print("\nĐối chiếu top-5 với bản gốc: khớp toàn bộ.")

    if args.json_path:
        payload = {
            "dictionary_size": len(dictionary),
            "load_ms": round(load_ms, 3),
            "index_build_ms": round(build_ms, 3),
            "limit": args.limit,
            "summary": {
                "mean_ms": round(statistics.fmean(times), 3),
                "p50_ms": round(percentile(times, 0.5), 3),
                "p95_ms": round(percentile(times, 0.95), 3),
                "min_ms": round(min(times), 3),
                "max_ms": round(max(times), 3),
                "cache_hit_ms": round(warm_ms, 3),
            },
            "worst_case": {
                "query": args.worst_case,
                "ms": round(worst_ms, 3),
                "evaluated": worst_result.evaluated,
            },
            "queries": optimized,
        }
        Path(args.json_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Đã ghi JSON: {args.json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
