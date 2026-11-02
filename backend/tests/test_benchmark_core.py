"""Kiểm tra phần lõi của benchmark: quét toàn bộ, đo, kho lưu và CSV."""

from __future__ import annotations

from app.core.benchmark import (
    DEFAULT_QUERIES,
    BenchmarkRun,
    BenchmarkStore,
    naive_top_k,
    run_benchmark,
    run_to_csv,
)
from app.core.dictionary import KeywordDictionary
from app.core.suggester import KeywordSuggester


def _suggester() -> tuple[KeywordSuggester, KeywordDictionary]:
    dictionary = KeywordDictionary(
        [
            "điện thoại samsung",
            "điện thoại samsung giá rẻ",
            "điện thoại apple",
            "tai nghe bluetooth",
            "tai nghe có dây",
            "áo thun akko",
            "bàn phím cơ",
        ]
    )
    return KeywordSuggester(dictionary, cache_size=0), dictionary


def test_naive_top_k_sorts_by_distance_then_keyword() -> None:
    _, dictionary = _suggester()

    hits = naive_top_k(dictionary, "áo thun akko", limit=3)

    assert hits[0] == ("áo thun akko", 0)
    assert hits == tuple(sorted(hits, key=lambda item: (item[1], item[0])))


def test_naive_top_k_matches_suggester() -> None:
    suggester, dictionary = _suggester()

    for query in ("điện thoại samsung", "tai nghe blutooth", "bàn phím"):
        expected = naive_top_k(dictionary, query, limit=3)
        result = suggester.suggest(query, limit=3)
        assert tuple((item.keyword, item.distance) for item in result.suggestions) == expected


def test_run_benchmark_summary() -> None:
    suggester, dictionary = _suggester()

    run = run_benchmark(
        suggester,
        dictionary,
        ["tai nghe blutooth", "áo thun akko"],
        limit=2,
        repeats=2,
    )

    assert run.status == "completed"
    assert len(run.measurements) == 2
    assert run.summary["query_count"] == 2
    assert run.summary["min_ms"] <= run.summary["mean_ms"] <= run.summary["max_ms"]
    assert run.summary["baseline_mean_ms"] is None
    assert run.summary["speedup_vs_baseline"] is None
    assert all(item.candidates >= 1 for item in run.measurements)


def test_run_benchmark_with_baseline_detects_parity() -> None:
    suggester, dictionary = _suggester()

    run = run_benchmark(
        suggester,
        dictionary,
        ["tai nghe blutooth", "áo thun akko"],
        limit=3,
        include_baseline=True,
    )

    assert run.summary["baseline_mismatches"] == 0
    assert run.summary["baseline_mean_ms"] is not None
    assert run.summary["speedup_vs_baseline"] is not None
    assert run.summary["speedup_vs_baseline"] > 0


def test_default_queries_are_available() -> None:
    assert len(DEFAULT_QUERIES) == 5
    assert all(isinstance(item, str) and item for item in DEFAULT_QUERIES)


def test_store_evicts_oldest_run() -> None:
    store = BenchmarkStore(capacity=2)
    runs = [
        BenchmarkRun(
            run_id=f"run{index}",
            status="completed",
            created_at=float(index),
            duration_ms=1.0,
            limit=5,
            repeats=1,
            include_baseline=False,
            measurements=(),
            summary={},
        )
        for index in range(3)
    ]

    for run in runs:
        store.add(run)

    assert len(store) == 2
    assert store.get("run0") is None
    assert store.get("run2") is not None
    assert store.ids() == ["run1", "run2"]


def test_csv_export() -> None:
    suggester, dictionary = _suggester()
    run = run_benchmark(suggester, dictionary, ["áo thun akko"], limit=2, include_baseline=True)

    csv_text = run_to_csv(run)
    lines = csv_text.strip().splitlines()

    assert lines[0].startswith("run_id,query,rank,keyword,distance")
    assert len(lines) == 1 + len(run.measurements[0].suggestions)
    assert run.run_id in lines[1]
    assert "áo thun akko" in lines[1]


def test_run_benchmark_clears_cache_between_measurements() -> None:
    suggester, dictionary = _suggester()

    run = run_benchmark(suggester, dictionary, ["tai nghe blutooth"], limit=2, repeats=3)

    # Không lần đo nào được phép là cache hit.
    assert run.measurements[0].candidates > 0
    assert run.measurements[0].took_ms > 0
    assert suggester.cache_stats()["hits"] == 0
