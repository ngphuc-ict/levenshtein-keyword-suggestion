import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import traceback
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from algorithm import LevenshteinSuggester
from app.core.dictionary import KeywordDictionary
from app.core.suggester import KeywordSuggester
from benchmarks.benchmark import build_queries, measure, percentile


class Tee:
    def __init__(self, terminal, log):
        self.terminal, self.log = terminal, log

    def write(self, text):
        self.terminal.write(text)
        self.log.write(text)
        self.flush()
        return len(text)

    def flush(self):
        self.terminal.flush()
        self.log.flush()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(values):
    return {
        "count": len(values),
        "mean_ms": statistics.fmean(values),
        "p50_ms": statistics.median(values),
        "p95_ms": percentile(values, 0.95),
        "min_ms": min(values),
        "max_ms": max(values),
    }


def paired_summary(rows):
    baseline = statistics.fmean(r["baseline_ms"] for r in rows)
    optimized = statistics.fmean(r["optimized_ms"] for r in rows)
    return {"observations": len(rows), "baseline_mean_ms": baseline,
            "optimized_mean_ms": optimized, "speedup": baseline / optimized}


def hardware():
    result = {"os": platform.platform(), "processor": platform.processor(),
              "logical_cpu_count": os.cpu_count(), "ram_bytes": None}
    try:
        command = ("$c=Get-CimInstance Win32_Processor; "
                   "$s=Get-CimInstance Win32_ComputerSystem; "
                   "@{cpu=($c.Name -join '; ');ram_bytes=[long]$s.TotalPhysicalMemory} "
                   "| ConvertTo-Json -Compress")
        result.update(json.loads(subprocess.check_output(
            ["powershell.exe", "-NoProfile", "-Command", command],
            text=True, timeout=30)))
    except Exception as error:
        result["hardware_collection_error"] = str(error)
    return result


def run():
    dataset = ROOT / "dictionary.txt"
    source_paths = ["algorithm.py", "backend/app/core/suggester.py",
                    "backend/app/core/trie.py", "backend/app/core/levenshtein.py",
                    "backend/app/core/text.py", "backend/app/core/dictionary.py",
                    "backend/benchmarks/benchmark.py"]
    before = {p: digest(ROOT / p) for p in source_paths}
    data = {
        "status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git("rev-parse", "HEAD"), "git_status_before": git("status", "--short"),
        "python_version": sys.version, "python_executable": sys.executable,
        "hardware": hardware(), "source_sha256": before,
        "algorithm": {
            "optimized": "KeywordSuggester: folded PrefixTrie + prefix DP + top-k ranking",
            "baseline": "algorithm.LevenshteinSuggester.rank_suggestions: full dictionary scan, prefix/full DP, heapq.nsmallest",
            "ranking": ["folded_prefix_distance", "not_starts_a_word", "accented_prefix_distance", "accented_full_distance", "keyword"],
            "trigram_used": False,
        },
        "configuration": {"queries": 20, "runs": 3, "top_k": 5, "seed": 42,
                          "cache_size": 256, "clear_cache_before_each_query": True,
                          "baseline_scope": "all 20 queries in each of 3 runs",
                          "timing": "perf_counter around each complete function call; no HTTP",
                          "p50": "statistics.median", "p95": "existing percentile: sorted[round(0.95*(n-1))]",
                          "primary_statistics": "statistics over 20 per-query means across 3 runs"},
        "dataset": {"path": "dictionary.txt", "sha256": digest(dataset),
                    "raw_lines": len(dataset.read_text(encoding="utf-8").splitlines())},
        "queries": [], "runs": [], "additional_parity_checks": [], "errors": [],
    }
    print("FINAL BENCHMARK", data["started_at"], flush=True)
    print(json.dumps({k: data[k] for k in ("git_commit", "python_version", "hardware", "configuration")}, ensure_ascii=False))
    reference = LevenshteinSuggester()

    def compare(suggester, words, query, label):
        suggester.clear_cache()
        optimized_ms, result = measure(lambda: suggester.suggest(query, limit=5))
        baseline_ms, baseline = measure(lambda: reference.rank_suggestions(query, words, limit=5))
        optimized_top = [{"keyword": x.keyword, "distance": x.distance} for x in result.suggestions]
        baseline_top = [{"keyword": x.keyword, "distance": x.distance} for x in baseline]
        row = {"query": query, "optimized_ms": optimized_ms, "baseline_ms": baseline_ms,
               "speedup": baseline_ms / optimized_ms, "cached": result.cached,
               "evaluated_candidates": result.evaluated, "optimized_top5": optimized_top,
               "baseline_top5": baseline_top, "parity": optimized_top == baseline_top}
        if result.cached:
            raise RuntimeError("Unexpected cache hit: " + repr(query))
        print(label, json.dumps(row, ensure_ascii=False), flush=True)
        return row

    try:
        for number in range(1, 4):
            load_ms, dictionary = measure(lambda: KeywordDictionary.from_file(dataset))
            build_ms, suggester = measure(lambda: KeywordSuggester(dictionary, cache_size=256))
            words = list(dictionary.keywords)
            queries = build_queries(words, 20, random.Random(42))
            if not data["queries"]:
                data["queries"] = queries
                data["dataset"]["normalized_unique_keywords"] = len(dictionary)
            assert queries == data["queries"]
            assert len(dictionary) == data["dataset"]["normalized_unique_keywords"]
            current = {"run": number, "load_and_normalize_ms": load_ms,
                       "index_and_service_build_ms": build_ms, "results": []}
            data["runs"].append(current)
            print(f"RUN {number}: keywords={len(dictionary)}, load={load_ms:.6f} ms, trie/service={build_ms:.6f} ms")
            for query in queries:
                current["results"].append(compare(suggester, words, query, f"RUN {number}"))
            current["hard_query"] = compare(suggester, words, "nồi cơm điện tử", f"HARD RUN {number}")
            current["optimized_statistics"] = stats([r["optimized_ms"] for r in current["results"]])
            current["paired_all_20"] = paired_summary(current["results"])
            current["paired_fixed_5"] = paired_summary(current["results"][:5])
        for query in ["dien thoai samsng", "dien tho", "điện tho",
                      unicodedata.normalize("NFD", "điện thoại samsng")]:
            data["additional_parity_checks"].append(compare(suggester, words, query, "EXTRA PARITY"))
        rows = [r for run in data["runs"] for r in run["results"]]
        averages = []
        for index, query in enumerate(data["queries"]):
            samples = [run["results"][index] for run in data["runs"]]
            paired = paired_summary(samples)
            averages.append({"query": query, "optimized_ms": paired["optimized_mean_ms"],
                             "baseline_ms": paired["baseline_mean_ms"], "speedup": paired["speedup"],
                             "parity": all(r["parity"] for r in samples)})
        all_checks = rows + [r["hard_query"] for r in data["runs"]] + data["additional_parity_checks"]
        data["per_query_averages"] = averages
        data["summary"] = {
            "successful_runs": len(data["runs"]),
            "optimized_over_query_means": stats([r["optimized_ms"] for r in averages]),
            "optimized_pooled_60": stats([r["optimized_ms"] for r in rows]),
            "paired_all_20": paired_summary(rows),
            "paired_fixed_5": paired_summary([r for run in data["runs"] for r in run["results"][:5]]),
            "hard_query": stats([r["hard_query"]["optimized_ms"] for r in data["runs"]]),
            "parity_comparisons": len(all_checks),
            "mismatches": [r for r in all_checks if not r["parity"]],
            "main_mismatch_count": sum(not r["parity"] for r in rows),
            "all_cache_misses": all(not r["cached"] for r in all_checks),
        }
        measured = data["summary"]["optimized_over_query_means"]
        targets = [("mean_ms", 12.68, measured["mean_ms"]),
                   ("p50_ms", 7.16, measured["p50_ms"]),
                   ("p95_ms", 71.22, measured["p95_ms"]),
                   ("hard_query_ms", 107.0, data["summary"]["hard_query"]["mean_ms"]),
                   ("paired_fixed_5_speedup", 456.0, data["summary"]["paired_fixed_5"]["speedup"])]
        data["comparison_to_user_supplied_figures"] = [
            {"metric": name, "reference": old, "measured": new, "delta": new-old,
             "delta_percent": (new-old)/old*100,
             "status": "MATCH" if abs(new-old)/old <= 0.10 else "DIFFERENT"}
            for name, old, new in targets]
        data["comparison_rule"] = "Descriptive +/-10% tolerance, not a statistical equivalence test; Word not opened."
        data["source_and_dataset_unchanged"] = (before == {p: digest(ROOT / p) for p in source_paths}
                                                 and data["dataset"]["sha256"] == digest(dataset))
        assert data["source_and_dataset_unchanged"]
        data["status"] = "completed_with_mismatches" if data["summary"]["mismatches"] else "completed"
        print("SUMMARY", json.dumps(data["summary"], ensure_ascii=False))
        print("REFERENCE COMPARISON", json.dumps(data["comparison_to_user_supplied_figures"], ensure_ascii=False))
    except Exception as error:
        data["status"] = "failed"
        data["errors"].append(repr(error))
        traceback.print_exc()
    data["finished_at"] = datetime.now(timezone.utc).isoformat()
    with (OUT / "benchmark-results.json").open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
    write_summary(data)
    print("FINAL STATUS", data["status"], "Artifacts:", OUT)
    return 0 if data["status"] == "completed" else 1


def write_summary(data):
    lines = ["# Benchmark cuối cùng — kết quả thực nghiệm", "",
             f"- Trạng thái: **{data['status']}**; commit `{data['git_commit']}`.",
             f"- Python: {data['python_version']}; executable `{data['python_executable']}`.",
             f"- Máy đo: `{json.dumps(data['hardware'], ensure_ascii=False)}`.",
             f"- Dataset: `dictionary.txt`, {data['dataset'].get('normalized_unique_keywords', 'chưa xác minh')} keyword sau chuẩn hóa; SHA-256 `{data['dataset']['sha256']}`.",
             "- 20 query giống nhau ở 3 vòng, seed 42, top-k=5; baseline đo cả 20 query mỗi vòng.",
             "- Runner tái sử dụng build_queries/measure/percentile từ `backend/benchmarks/benchmark.py`; không sửa thuật toán.",
             "- Optimized: `backend/app/core/suggester.py:KeywordSuggester` → PrefixTrie + prefix DP + top-k; không dùng Trigram.",
             "- Baseline: `algorithm.py:LevenshteinSuggester.rank_suggestions`, quét toàn dictionary, normalize từng keyword, prefix/full DP, heapq.nsmallest.",
             "- Cả hai dùng cùng tuple keyword chuẩn hóa; điểm hiển thị là prefix không dấu, tie-break có dấu/full-distance/chữ cái.", "",
             "## Phương pháp", "",
             "- Đo perf_counter quanh lời gọi đầy đủ, cùng process, đơn luồng, không HTTP; mỗi query xóa LRU trước optimized và xác nhận cached=false.",
             "- Thứ tự cố định: optimized rồi baseline cho từng query; không warm-up riêng. Cache miss chỉ là LRU ứng dụng, không phải cache CPU/OS.",
             "- Nạp/normalize/dedup/sort/by_length và dựng trie/service được đo riêng mỗi vòng, ngoài query latency; không dùng DictionaryStats.load_ms nội bộ.",
             "- Số chính: thống kê trên 20 giá trị thời gian trung bình từng query qua 3 vòng. JSON còn có thống kê mỗi vòng và pooled 60 mẫu.",
             "- p50 dùng statistics.median; p95 dùng hàm có sẵn sorted[round(0.95*(n-1))], không nội suy.",
             "- Speedup = tổng baseline / tổng optimized trên đúng các cặp cùng query/lần chạy; không chia trung bình hai tập khác nhau.",
             "- Query khó và 4 query kiểm tra Unicode/không dấu/gõ dở bổ sung được tách khỏi 20 query thống kê.", ""]
    if "summary" in data:
        s = data["summary"]
        lines += ["## Tổng hợp", "", "| Phạm vi | Mean ms | p50 ms | p95 ms | Min ms | Max ms |", "|---|---:|---:|---:|---:|---:|"]
        for label, values in [("20 query, trung bình 3 vòng", s["optimized_over_query_means"]),
                              ("60 phép đo pooled", s["optimized_pooled_60"]),
                              ("Query khó, 3 phép đo", s["hard_query"])]:
            lines.append(f"| {label} | " + " | ".join(f"{values[k]:.6f}" for k in ("mean_ms", "p50_ms", "p95_ms", "min_ms", "max_ms")) + " |")
        lines += ["", "| Vòng | Load/normalize ms | Trie/service ms | Mean ms | p50 ms | p95 ms |", "|---|---:|---:|---:|---:|---:|"]
        for r in data["runs"]:
            v = r["optimized_statistics"]
            lines.append(f"| {r['run']} | {r['load_and_normalize_ms']:.6f} | {r['index_and_service_build_ms']:.6f} | {v['mean_ms']:.6f} | {v['p50_ms']:.6f} | {v['p95_ms']:.6f} |")
        lines += ["", "## Baseline vs Optimized — trung bình 3 vòng", "", "| Query | Baseline ms | Optimized ms | Speedup | Parity |", "|---|---:|---:|---:|---|"]
        for r in data["per_query_averages"]:
            lines.append(f"| {r['query']} | {r['baseline_ms']:.6f} | {r['optimized_ms']:.6f} | {r['speedup']:.3f}× | {'MATCH' if r['parity'] else 'MISMATCH'} |")
        for label, key in [("Toàn bộ 20 query × 3", "paired_all_20"), ("5 query cố định × 3", "paired_fixed_5")]:
            p = s[key]
            lines.append(f"\n- {label}: baseline mean {p['baseline_mean_ms']:.6f} ms; optimized mean {p['optimized_mean_ms']:.6f} ms; speedup **{p['speedup']:.3f}×**.")
        lines += ["", "## Tính đúng đắn và query khó", "",
                  f"- {s['parity_comparisons']} lần đối chiếu ordered top-5, cả keyword và distance; mismatch: **{len(s['mismatches'])}**; toàn bộ cache miss: {s['all_cache_misses']}.",
                  "- Query khó: `nồi cơm điện tử`; bảng tổng hợp tách riêng, raw baseline/optimized và top-5 lưu từng vòng trong JSON.",
                  "- Query cố định có dấu/sai ký tự và các query bổ sung dưới đây được đối chiếu cùng baseline:"]
        for r in data["additional_parity_checks"]:
            lines.append(f"  - `{r['query']}` ({ascii(r['query'])}): {'MATCH' if r['parity'] else 'MISMATCH'}.")
        for r in s["mismatches"]:
            lines.append("- MISMATCH RAW: `" + json.dumps(r, ensure_ascii=False) + "`")
        lines += ["", "## Đối chiếu số liệu được cung cấp", "",
                  "Chưa đọc/xác minh trực tiếp Word: **NOT_VERIFIABLE** về nguồn số liệu. Bảng dưới chỉ so với 5 giá trị trong yêu cầu, dùng dung sai mô tả ±10% (không phải kiểm định thống kê).", "",
                  "| Chỉ số | Tham chiếu | Đo mới | Chênh lệch | Chênh % | Đánh giá |", "|---|---:|---:|---:|---:|---|"]
        for c in data["comparison_to_user_supplied_figures"]:
            lines.append(f"| {c['metric']} | {c['reference']:.3f} | {c['measured']:.6f} | {c['delta']:+.6f} | {c['delta_percent']:+.2f}% | {c['status']} |")
        lines += ["", "## Nhận xét và giới hạn", "",
                  "- Trie chia sẻ DP tiền tố và cắt nhánh; ranking chỉ tính thêm điểm cần thiết. Speedup đo so với baseline có cả chi phí normalize/fold lặp lại, không chỉ riêng một kernel DP.",
                  "- Query khó có thể duyệt nhiều nhánh và nới ngưỡng nhiều lần; evaluated_candidates không phải số nút/ô DP và không cộng toàn bộ vòng tìm kiếm.",
                  "- CPU/OS/Python, tải nền, thứ tự query, bộ query/seed và phương pháp percentile có thể ảnh hưởng; không đủ bằng chứng xác định nguyên nhân chênh số liệu cũ.",
                  "- Ba vòng cùng máy/process không chứng minh tốc độ trên mọi môi trường; không đo network/API/UI, không dùng số cũ làm kết quả mới.",
                  f"- Hash source và dataset giữ nguyên sau benchmark: {data['source_and_dataset_unchanged']}."]
    else:
        lines += ["## Lỗi", "", *[str(error) for error in data["errors"]]]
    lines += ["", "## Bằng chứng tái lập", "", "```powershell", "& backend/.venv/Scripts/python.exe -B -u report/final-benchmark/run_final_benchmark.py", "```", "",
              "Runner không ghi đè artifact có sẵn; muốn chạy lại phải chọn thư mục kết quả mới trong bản sao runner. JSON chứa raw timing, hai top-5 và parity; TXT là stdout/stderr thực tế được tee nguyên văn."]
    with (OUT / "benchmark-summary.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    targets = [OUT / name for name in ("benchmark-results.json", "benchmark-summary.md", "benchmark-output.txt")]
    if any(path.exists() for path in targets):
        raise SystemExit("Refusing to overwrite existing benchmark artifacts")
    with targets[2].open("x", encoding="utf-8") as log:
        with contextlib.redirect_stdout(Tee(sys.stdout, log)), contextlib.redirect_stderr(Tee(sys.stderr, log)):
            raise SystemExit(run())
