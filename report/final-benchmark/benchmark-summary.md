# Benchmark cuối cùng — kết quả thực nghiệm

- Trạng thái: **completed**; commit `75accab0ce777ad12e94c0a8fd8d04ccbd36c971`.
- Python: 3.14.8 (tags/v3.14.8:8e6e75d, Sep 30 2026, 18:19:33) [MSC v.1944 64 bit (AMD64)]; executable `D:\CMC year 3\Ptich_tke_giai_thuat\DeTai6\levenshtein-keyword-suggestion\backend\.venv\Scripts\python.exe`.
- Máy đo: `{"os": "Windows-11-10.0.26300-SP0", "processor": "AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD", "logical_cpu_count": 16, "ram_bytes": 16438382592, "cpu": "AMD Ryzen 7 8745H with Radeon 780M Graphics"}`.
- Dataset: `dictionary.txt`, 23850 keyword sau chuẩn hóa; SHA-256 `aa5aa53656073c8701e266e627b4d809ae2b90f00451b94643ab06c41f2219f1`.
- 20 query giống nhau ở 3 vòng, seed 42, top-k=5; baseline đo cả 20 query mỗi vòng.
- Runner tái sử dụng build_queries/measure/percentile từ `backend/benchmarks/benchmark.py`; không sửa thuật toán.
- Optimized: `backend/app/core/suggester.py:KeywordSuggester` → PrefixTrie + prefix DP + top-k; không dùng Trigram.
- Baseline: `algorithm.py:LevenshteinSuggester.rank_suggestions`, quét toàn dictionary, normalize từng keyword, prefix/full DP, heapq.nsmallest.
- Cả hai dùng cùng tuple keyword chuẩn hóa; điểm hiển thị là prefix không dấu, tie-break có dấu/full-distance/chữ cái.

## Phương pháp

- Đo perf_counter quanh lời gọi đầy đủ, cùng process, đơn luồng, không HTTP; mỗi query xóa LRU trước optimized và xác nhận cached=false.
- Thứ tự cố định: optimized rồi baseline cho từng query; không warm-up riêng. Cache miss chỉ là LRU ứng dụng, không phải cache CPU/OS.
- Nạp/normalize/dedup/sort/by_length và dựng trie/service được đo riêng mỗi vòng, ngoài query latency; không dùng DictionaryStats.load_ms nội bộ.
- Số chính: thống kê trên 20 giá trị thời gian trung bình từng query qua 3 vòng. JSON còn có thống kê mỗi vòng và pooled 60 mẫu.
- p50 dùng statistics.median; p95 dùng hàm có sẵn sorted[round(0.95*(n-1))], không nội suy.
- Speedup = tổng baseline / tổng optimized trên đúng các cặp cùng query/lần chạy; không chia trung bình hai tập khác nhau.
- Query khó và 4 query kiểm tra Unicode/không dấu/gõ dở bổ sung được tách khỏi 20 query thống kê.

## Tổng hợp

| Phạm vi | Mean ms | p50 ms | p95 ms | Min ms | Max ms |
|---|---:|---:|---:|---:|---:|
| 20 query, trung bình 3 vòng | 24.015812 | 13.814917 | 132.062467 | 1.415500 | 133.606467 |
| 60 phép đo pooled | 24.015812 | 13.645650 | 129.485200 | 1.145500 | 153.410100 |
| Query khó, 3 phép đo | 181.153533 | 181.049700 | 185.024000 | 177.386900 | 185.024000 |

| Vòng | Load/normalize ms | Trie/service ms | Mean ms | p50 ms | p95 ms |
|---|---:|---:|---:|---:|---:|
| 1 | 47.264900 | 124.490900 | 23.179810 | 13.532950 | 122.460700 |
| 2 | 52.482100 | 157.867800 | 25.762010 | 14.599000 | 134.163100 |
| 3 | 57.926700 | 155.090600 | 23.105615 | 13.706900 | 124.948600 |

## Baseline vs Optimized — trung bình 3 vòng

| Query | Baseline ms | Optimized ms | Speedup | Parity |
|---|---:|---:|---:|---|
| điện thoại samsng | 3720.770900 | 2.367700 | 1571.471× | MATCH |
| tai nghe blutooth | 3575.812133 | 12.107600 | 295.336× | MATCH |
| áo thun akko | 2555.073700 | 1.415500 | 1805.068× | MATCH |
| laptop dell i5 | 2925.937267 | 2.227633 | 1313.473× | MATCH |
| bàn phím cơ | 2388.306433 | 15.947067 | 149.765× | MATCH |
| điện thopại hp màu nâu | 4476.899067 | 3.477533 | 1287.378× | MATCH |
| kínẽ cường lực cao cấp | 4540.199000 | 14.087500 | 322.286× | MATCH |
| túi xách iphoce màu xám | 4657.398100 | 4.383567 | 1062.468× | MATCH |
| bàn di ẩchuột corsair màu hồng | 5968.919200 | 22.059533 | 270.582× | MATCH |
| webcamếrazer có dây | 3792.213033 | 9.102200 | 416.626× | MATCH |
| iện thoại opơo mà bạc | 4178.778833 | 11.367167 | 367.618× | MATCH |
| cáp ạc leogvo freeship | 4349.595167 | 13.007467 | 334.392× | MATCH |
| bàn phím raịzer ledrgb | 4345.624033 | 16.790667 | 258.812× | MATCH |
| laptop sandiskậmini | 3775.277200 | 13.542333 | 278.776× | MATCH |
| chuột không dây lsgòfreeship | 5537.215700 | 20.487067 | 270.279× | MATCH |
| mà hình sandisk màu ơneâu | 4957.536567 | 16.334567 | 303.500× | MATCH |
| kính cườg lực lenovo màu vàng | 5719.154700 | 15.536400 | 368.113× | MATCH |
| smartatch mcbook bluertooth | 5455.240567 | 132.062467 | 41.308× | MATCH |
| ốpẵlưậglsony chính hãng | 4719.773467 | 133.606467 | 35.326× | MATCH |
| sạc dự phòng ankeơ c dây | 4837.588400 | 20.405800 | 237.069× | MATCH |

- Toàn bộ 20 query × 3: baseline mean 4323.865673 ms; optimized mean 24.015812 ms; speedup **180.042×**.

- 5 query cố định × 3: baseline mean 3033.180087 ms; optimized mean 6.813100 ms; speedup **445.198×**.

## Tính đúng đắn và query khó

- 67 lần đối chiếu ordered top-5, cả keyword và distance; mismatch: **0**; toàn bộ cache miss: True.
- Query khó: `nồi cơm điện tử`; bảng tổng hợp tách riêng, raw baseline/optimized và top-5 lưu từng vòng trong JSON.
- Query cố định có dấu/sai ký tự và các query bổ sung dưới đây được đối chiếu cùng baseline:
  - `dien thoai samsng` ('dien thoai samsng'): MATCH.
  - `dien tho` ('dien tho'): MATCH.
  - `điện tho` ('\u0111i\u1ec7n tho'): MATCH.
  - `điện thoại samsng` ('\u0111ie\u0323\u0302n thoa\u0323i samsng'): MATCH.

## Đối chiếu số liệu được cung cấp

Chưa đọc/xác minh trực tiếp Word: **NOT_VERIFIABLE** về nguồn số liệu. Bảng dưới chỉ so với 5 giá trị trong yêu cầu, dùng dung sai mô tả ±10% (không phải kiểm định thống kê).

| Chỉ số | Tham chiếu | Đo mới | Chênh lệch | Chênh % | Đánh giá |
|---|---:|---:|---:|---:|---|
| mean_ms | 12.680 | 24.015812 | +11.335812 | +89.40% | DIFFERENT |
| p50_ms | 7.160 | 13.814917 | +6.654917 | +92.95% | DIFFERENT |
| p95_ms | 71.220 | 132.062467 | +60.842467 | +85.43% | DIFFERENT |
| hard_query_ms | 107.000 | 181.153533 | +74.153533 | +69.30% | DIFFERENT |
| paired_fixed_5_speedup | 456.000 | 445.198234 | -10.801766 | -2.37% | MATCH |

## Nhận xét và giới hạn

- Trie chia sẻ DP tiền tố và cắt nhánh; ranking chỉ tính thêm điểm cần thiết. Speedup đo so với baseline có cả chi phí normalize/fold lặp lại, không chỉ riêng một kernel DP.
- Query khó có thể duyệt nhiều nhánh và nới ngưỡng nhiều lần; evaluated_candidates không phải số nút/ô DP và không cộng toàn bộ vòng tìm kiếm.
- CPU/OS/Python, tải nền, thứ tự query, bộ query/seed và phương pháp percentile có thể ảnh hưởng; không đủ bằng chứng xác định nguyên nhân chênh số liệu cũ.
- Ba vòng cùng máy/process không chứng minh tốc độ trên mọi môi trường; không đo network/API/UI, không dùng số cũ làm kết quả mới.
- Hash source và dataset giữ nguyên sau benchmark: True.

## Bằng chứng tái lập

```powershell
& backend/.venv/Scripts/python.exe -B -u report/final-benchmark/run_final_benchmark.py
```

Runner không ghi đè artifact có sẵn; muốn chạy lại phải chọn thư mục kết quả mới trong bản sao runner. JSON chứa raw timing, hai top-5 và parity; TXT là stdout/stderr thực tế được tee nguyên văn.
