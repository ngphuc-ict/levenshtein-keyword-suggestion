# Backend — Gợi ý từ khóa bằng Levenshtein

REST API bọc thuật toán gợi ý từ khóa của repo (`algorithm.py`, `data_processor.py`)
thành một dịch vụ chạy được thật: nạp từ điển 23.850 từ khóa một lần khi khởi
động, trả về top-5 từ khóa gần nhất cho mỗi truy vấn, kèm tài liệu OpenAPI,
bộ đệm, kiểm thử và đo hiệu năng.

- Framework: **FastAPI** (Python 3.10+), chạy bằng **Uvicorn**.
- Kết quả **trùng khớp tuyệt đối** với bản `algorithm.py` của nhóm — có test
  đối chiếu tự động trên toàn bộ từ điển.
- Thời gian phản hồi điển hình **3–25 ms** (bản gốc quét toàn bộ: ~600 ms).

---

## 1. Chạy nhanh

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --no-access-log
```

Mở các địa chỉ sau:

| Địa chỉ | Nội dung |
| --- | --- |
| <http://127.0.0.1:8000/> | Trang demo nhập từ khóa và xem gợi ý |
| <http://127.0.0.1:8000/docs> | Swagger UI — gọi thử API trực tiếp |
| <http://127.0.0.1:8000/redoc> | Tài liệu ReDoc |
| <http://127.0.0.1:8000/api/v1/health> | Kiểm tra dịch vụ |

Hoặc dùng `make`:

```bash
make install     # tạo venv + cài phụ thuộc
make dev         # uvicorn --reload tại cổng 8000
make test        # chạy 69 test
make bench       # đo hiệu năng so với bản gốc
```

Thử nhanh bằng curl:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/suggest \
  -H 'Content-Type: application/json' \
  -d '{"query": "điện thoại samsng", "limit": 5}'
```

---

## 2. API

### `POST /api/v1/suggest`

Body:

| Trường | Kiểu | Mặc định | Ghi chú |
| --- | --- | --- | --- |
| `query` | string | bắt buộc | 1–200 ký tự, giữ dấu tiếng Việt |
| `limit` | int | `5` | 1–20 |
| `max_distance` | int \| null | `null` | chỉ nhận gợi ý có khoảng cách ≤ giá trị này |

Ví dụ:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/suggest \
  -H 'Content-Type: application/json' \
  -d '{"query": "điện thoại samsng", "limit": 5}'
```

```json
{
  "query": "điện thoại samsng",
  "normalized_query": "điện thoại samsng",
  "suggestions": [
    { "keyword": "điện thoại samsung", "distance": 1 },
    { "keyword": "điện thoại gaming", "distance": 2 },
    { "keyword": "điện thoại asus", "distance": 4 },
    { "keyword": "điện thoại mini", "distance": 4 },
    { "keyword": "điện thoại msi", "distance": 4 }
  ],
  "count": 5,
  "limit": 5,
  "max_distance": null,
  "took_ms": 10.5,
  "cached": false,
  "evaluated_candidates": 186
}
```

`took_ms` và `evaluated_candidates` không bắt buộc với frontend, nhưng hữu ích
khi demo/báo cáo: chúng cho thấy bộ lọc đã loại bỏ bao nhiêu từ khóa.

### `GET /api/v1/suggest`

Biến thể tiện cho trình duyệt/curl: `/api/v1/suggest?q=tai+nghe+blutooth&limit=3`.

### `GET /api/v1/health`

```json
{ "status": "ok", "version": "1.0.0", "dictionary_size": 23850, "uptime_seconds": 4.4 }
```

### `GET /api/v1/stats`

Số liệu phục vụ báo cáo: kích thước từ điển, thời gian nạp, cấu hình thuật toán
và tỉ lệ cache hit.

### Hợp đồng API cho UI (theo `UI/src/API_List.md`)

Frontend liệt kê các đường dẫn không có tiền tố `/api/v1`; backend phục vụ
đúng những đường dẫn đó và chúng gọi lại cùng logic với nhóm `/api/v1`, nên
kết quả không bao giờ lệch nhau.

| Phương thức | Đường dẫn | Chức năng |
| --- | --- | --- |
| GET | `/health` | Tương đương `/api/v1/health` |
| GET | `/search/suggest?q=...&limit=5` | Gợi ý mờ (Levenshtein) — dùng cho ô nhập liệu |
| GET | `/search?q=...&limit=20&mode=contains\|prefix` | Tìm từ khóa chứa/bắt đầu bằng chuỗi |
| GET | `/dictionary?page=1&page_size=50&q=&length=&sort=` | Duyệt từ điển, phân trang, lọc |
| GET | `/dictionary/stats` | Tương đương `/api/v1/stats` |
| GET | `/algorithm/distance?source=...&target=...` | Khoảng cách Levenshtein giữa hai chuỗi |
| POST | `/algorithm/visualize` | Bảng quy hoạch động đầy đủ + đường đi tối ưu |
| POST | `/benchmark/runs` | Chạy benchmark, lưu kết quả theo `run_id` |
| GET | `/benchmark/runs/{run_id}` | Xem lại kết quả một lần chạy |
| GET | `/benchmark/runs/{run_id}/export` | Tải CSV (UTF-8 BOM, mở được bằng Excel) |

Ví dụ:

```bash
curl "http://127.0.0.1:8000/search?q=tai%20nghe&limit=3"
curl "http://127.0.0.1:8000/dictionary?q=samsung&page_size=2"
curl "http://127.0.0.1:8000/algorithm/distance?source=Kitten&target=sitting"
curl -X POST http://127.0.0.1:8000/algorithm/visualize \
  -H 'Content-Type: application/json' -d '{"source": "kitten", "target": "sitting"}'
curl -X POST http://127.0.0.1:8000/benchmark/runs \
  -H 'Content-Type: application/json' \
  -d '{"queries": ["tai nghe blutooth"], "include_baseline": true}'
```

Vài quy ước đáng lưu ý:

- `/search` khớp **chuỗi con** (không tính khoảng cách) và trả về `total` là
  tổng số từ khóa khớp, `items` bị giới hạn bởi `limit`; sắp xếp theo vị trí
  khớp, rồi độ dài, rồi bảng chữ cái.
- `/algorithm/visualize` giới hạn mỗi chuỗi 60 ký tự (bảng tối đa 61×61 ô).
- `/benchmark/runs` xóa bộ đệm trước mỗi lần đo để không ghi nhận cache hit
  thành hiệu năng thật; `include_baseline` đo thêm mốc quét toàn bộ từ điển
  (mỗi truy vấn tốn thêm ~0,5–0,6 giây với từ điển đầy đủ) và tự đối chiếu
  top-k hai bên.
- `/benchmark/runs` giữ tối đa 20 lần chạy gần nhất trong bộ nhớ; khởi động
  lại dịch vụ là mất.

### Lỗi

Mọi lỗi trả về cùng một cấu trúc:

```json
{
  "error": "validation_error",
  "message": "Dữ liệu đầu vào không hợp lệ.",
  "details": [{ "field": "query", "message": "Truy vấn không được rỗng..." }]
}
```

| Mã | Khi nào |
| --- | --- |
| 422 | Thiếu/sai kiểu dữ liệu, `query` rỗng hoặc chỉ có ký tự đặc biệt, `limit` ngoài 1–20 |
| 404 | Sai đường dẫn |
| 500 | Lỗi không lường trước (đã ghi log kèm stack trace) |

---

## 3. Cấu trúc thư mục

```
backend/
├── app/
│   ├── main.py              # tạo FastAPI app, lifespan, middleware, xử lý lỗi
│   ├── config.py            # cấu hình từ biến môi trường
│   ├── schemas.py           # Pydantic request/response
│   ├── api/
│   │   ├── common.py        # hàm dùng chung (đóng gói response gợi ý)
│   │   ├── suggest.py       # POST/GET /suggest
│   │   ├── system.py        # /health, /stats (+ /health cho UI)
│   │   ├── search.py        # /search/suggest, /search
│   │   ├── dictionary.py    # /dictionary, /dictionary/stats
│   │   ├── algorithm.py     # /algorithm/distance, /algorithm/visualize
│   │   └── benchmark.py     # /benchmark/runs (+ xem lại, xuất CSV)
│   ├── core/
│   │   ├── text.py          # chuẩn hóa NFC, chữ thường, bỏ dấu câu
│   │   ├── levenshtein.py   # DP chuẩn, DP có chặn, bảng DP + truy vết
│   │   ├── dictionary.py    # nạp từ điển, chỉ mục theo độ dài
│   │   ├── index.py         # chỉ mục trigram lọc ứng viên
│   │   ├── suggester.py     # xếp hạng top-k, bộ đệm LRU
│   │   └── benchmark.py     # đo hiệu năng, kho lưu run, xuất CSV
│   └── static/index.html    # trang demo
├── tests/                   # 117 test: đơn vị, API, hợp đồng UI, đối chiếu gốc
├── benchmarks/benchmark.py  # đo hiệu năng + kiểm tra chéo kết quả
├── requirements.txt         # phụ thuộc chạy
├── requirements-dev.txt     # thêm pytest, httpx, ruff
├── pyproject.toml           # cấu hình pytest/ruff
├── Makefile
└── README.md
```

---

## 4. Thuật toán

### 4.1 Nền tảng: quy hoạch động Levenshtein

Với hai chuỗi `a` (truy vấn) và `b` (từ khóa):

```
D[0][j] = j,  D[i][0] = i
D[i][j] = min(
    D[i-1][j] + 1,                       # xóa
    D[i][j-1] + 1,                       # chèn
    D[i-1][j-1] + (a[i-1] != b[j-1])     # thay thế / giữ nguyên
)
```

Chỉ cần giữ hai hàng → bộ nhớ `O(min(m, n))`, thời gian `O(m·n)`. Đây chính là
công thức trong `algorithm.py`; backend giữ nguyên để kết quả không đổi.

Xếp hạng: sắp theo `(distance, keyword)` tăng dần, mỗi từ khóa chỉ tính một lần.
Nhờ vậy kết quả ổn định, không phụ thuộc thứ tự duyệt.

### 4.2 Vì sao phải tối ưu?

Quét cả 23.850 từ khóa với DP đầy đủ tốn ~600 ms mỗi truy vấn — quá chậm cho
một API. Backend thêm ba lớp tối ưu **không làm thay đổi kết quả**:

**a) Lọc ứng viên bằng trigram.** Mỗi chuỗi được đệm 2 khoảng trắng hai đầu rồi
cắt thành các trigram. Một phép chèn/xóa/thay thế chỉ phá hủy tối đa 3 trigram,
nên nếu `distance(q, k) ≤ d` thì:

```
|G(q) ∩ G(k)| ≥ |G(q)| − 3d
```

Đây là điều kiện **cần**, nên loại bỏ ứng viên theo ngưỡng này không bao giờ bỏ
sót kết quả đúng. Ngưỡng `d` được nới dần `1, 2, 3, ...` cho tới khi gom đủ
`limit` kết quả; lúc đó mọi từ khóa có khoảng cách ≤ ngưỡng đều đã được xét →
top-k **chính xác**, không phải gần đúng.

**b) Quy hoạch động có chặn (Ukkonen).** Khi chỉ cần biết khoảng cách có vượt
ngưỡng `d` hay không, chỉ những ô `|i − j| ≤ d` quanh đường chéo mới có thể mang
giá trị ≤ `d`. Bỏ phần ngoài dải → thời gian `O(m·d)`, bộ nhớ `O(d)`. Nếu cả
một hàng đều > `d` thì dừng ngay. Hàm trả về `d + 1` khi khoảng cách thật lớn
hơn ngưỡng, đủ để so sánh mà không cần tính chính xác.

**c) Quét dự phòng theo độ dài.** Với truy vấn quá ngắn hoặc quá xa từ vựng, bộ
lọc trigram hết tác dụng (`|G(q)| − 3d ≤ 0`); khi đó backend quét từ khóa theo
nhóm độ dài lệch dần. Vì `distance ≥ |Δlength|`, khi đã đủ `limit` kết quả với
khoảng cách tệ nhất `d` thì mọi nhóm lệch hơn `d` bị bỏ qua — vẫn đúng, chỉ
chậm hơn.

**d) Bộ đệm LRU.** Truy vấn lặp lại (người dùng gõ lại, demo trước lớp) trả về
trong ~0,02 ms; thống kê hit/miss nằm ở `/stats`.

### 4.3 Độ phức tạp

| Trường hợp | Thời gian |
| --- | --- |
| Một cặp chuỗi, DP đầy đủ | `O(m·n)` |
| Một cặp chuỗi, DP có chặn | `O(m·d)` |
| Truy vấn khớp gần (d nhỏ) | `O((m + số ứng viên)·d)` |
| Truy vấn xa từ vựng | `O(N·m·d)` — quét toàn bộ |

---

## 5. Hiệu năng đo được

Máy đo: Linux, Python 3.14, từ điển 23.850 từ khóa, `limit = 5`, không dùng cache.

| Truy vấn | Backend | Bản gốc `algorithm.py` | Nhanh hơn | Ứng viên đã tính |
| --- | ---: | ---: | ---: | ---: |
| `điện thoại samsng` | 10,5 ms | 673 ms | ×64 | 186 |
| `tai nghe blutooth` | 25,1 ms | 651 ms | ×26 | 809 |
| `áo thun akko` | 2,5 ms | 498 ms | ×199 | 84 |
| `laptop dell i5` | 3,1 ms | 550 ms | ×179 | 179 |
| `bàn phím cơ` | 3,3 ms | 482 ms | ×147 | 53 |

Với 20 truy vấn (5 mẫu trên + 15 truy vấn gõ sai ngẫu nhiên):

- trung bình **23,4 ms**, p50 **25,0 ms**, p95 **48,9 ms**;
- cache hit: **0,02 ms**;
- nạp từ điển + dựng chỉ mục lúc khởi động: **~105 ms**.

Trường hợp xấu: truy vấn không có từ khóa nào gần (ví dụ `nồi cơm điện tử`,
5 kết quả gần nhất đều cách 10 phép) → **~0,7 s** vì phải quét đầy đủ; vẫn trả
đúng kết quả. Đây là giới hạn của việc tính khoảng cách tuyệt đối trên toàn từ
điển bằng Python thuần, không phải lỗi của bộ lọc.

Chạy lại phép đo:

```bash
python benchmarks/benchmark.py                    # 20 truy vấn
python benchmarks/benchmark.py --naive 10 --json ket-qua.json
```

Script tự kiểm tra chéo top-5 với `algorithm.py` và báo lỗi nếu lệch.

---

## 6. Kiểm thử

```bash
python -m pytest            # 117 test, ~3,7 giây (độ phủ 100%)
python -m pytest -k api     # chỉ test API
```

Các nhóm test:

| File | Nội dung |
| --- | --- |
| `test_text.py` | Chuẩn hóa NFC/NFD, dấu câu, khoảng trắng, giá trị không hợp lệ |
| `test_levenshtein.py` | Ca kinh điển, đối xứng, DP có chặn khớp DP đầy đủ trên 500 cặp ngẫu nhiên |
| `test_dictionary.py` | Nạp, khử trùng lặp, chỉ mục độ dài, tệp thiếu/rỗng |
| `test_suggester.py` | So với brute-force, tie-break chữ cái, `limit`, `max_distance`, cache |
| `test_api.py` | Endpoint, validation, CORS, header truy vết, trang demo, lỗi 500/405 |
| `test_config.py` | Đọc biến môi trường, đường dẫn tương đối, cấu hình sai |
| `test_levenshtein_trace.py` | Bảng quy hoạch động và đường đi tối ưu trên 200 cặp ngẫu nhiên |
| `test_benchmark_core.py` | Quét toàn bộ, đo nguội, kho lưu run, CSV |
| `test_contract_api.py` | Toàn bộ nhóm endpoint theo `UI/src/API_List.md` |
| `test_parity_original.py` | Đối chiếu `algorithm.py` gốc: khoảng cách, chuẩn hóa, top-5 |

Test đối chiếu chạy cả trên toàn bộ 23.850 từ khóa với hai truy vấn mẫu trong
README, nên có thể yên tâm backend không làm sai lệch thuật toán của nhóm.

---

## 7. Cấu hình

| Biến môi trường | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `DICTIONARY_PATH` | `../dictionary.txt` | Đường dẫn từ điển (tương đối so với thư mục chạy) |
| `SUGGEST_CACHE_SIZE` | `1024` | Số mục tối đa trong LRU, `0` = tắt |
| `CORS_ORIGINS` | `*` | Danh sách origin, phân tách bằng dấu phẩy |
| `LOG_LEVEL` | `INFO` | Mức log |

Xem `.env.example`. Ứng dụng không tự đọc tệp `.env`; hãy export biến môi
trường hoặc dùng `env $(cat .env | xargs) uvicorn ...`.

---

## 8. Tích hợp với frontend

- Gọi `POST /api/v1/suggest` với JSON `{ "query": "...", "limit": 5 }`, hoặc
  `GET /search/suggest?q=...&limit=5` nếu muốn bám đúng `UI/src/API_List.md`.
- Bảng đối chiếu đường dẫn: xem mục **Hợp đồng API cho UI** ở trên.
- CORS đã mở cho mọi origin (đổi `CORS_ORIGINS` khi triển khai thật).
- Nên **debounce 250–300 ms** khi gợi ý theo từng ký tự để tránh gọi API liên tục.
- Kết quả đã sắp xếp sẵn: hiển thị theo đúng thứ tự nhận được.
- `distance = 0` nghĩa là khớp chính xác; có thể hiển thị khác đi để người dùng dễ thấy.
- Trang danh sách nên dùng `GET /dictionary` (phân trang) và `GET /search`
  (khớp chuỗi) thay vì gọi gợi ý mờ cho mọi ký tự.

Ví dụ JavaScript:

```js
const response = await fetch("http://127.0.0.1:8000/api/v1/suggest", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query: "điện thoại samsng", limit: 5 }),
});
const { suggestions } = await response.json();

// Hoặc bám đúng hợp đồng UI/src/API_List.md:
const quick = await fetch(
  "http://127.0.0.1:8000/search/suggest?q=" + encodeURIComponent("tai nghe blutooth") + "&limit=5"
).then((r) => r.json());
```

---

## 9. Hạn chế và hướng phát triển

- Chưa có xác thực/rate limit — phạm vi bài tập, không cần thiết.
- Từ điển nạp vào RAM và chỉ đọc; muốn cập nhật phải khởi động lại (hoặc thêm
  endpoint nạp lại có kiểm soát).
- Truy vấn xa từ vựng chấp nhận chậm hơn (~0,7 s) để giữ kết quả chính xác.
- Có thể thay DP Python bằng thư viện C (`rapidfuzz`) để nhanh hơn nữa, nhưng
  như vậy sẽ không còn là thuật toán tự cài đặt của môn học.
