# UI

## Chạy cùng backend

1. Khởi động backend từ thư mục `backend`:

   ```bash
   uvicorn app.main:app --reload --no-access-log
   ```

2. Khởi động giao diện từ thư mục `UI`:

   ```bash
   npm install
   npm run dev
   ```

Trong môi trường phát triển, Vite chuyển tiếp các request `/search` tới
`http://127.0.0.1:8000` cùng với `/dictionary` và `/benchmark`. Có thể đặt
`VITE_API_BASE_URL` để dùng địa chỉ backend khác, ví dụ
`VITE_API_BASE_URL=https://api.example.com`.

Trên Windows có thể chạy `run.bat` ở thư mục gốc repo để mở cả backend và UI.

## API đang dùng

- `GET /search/suggest?q=...&limit=5`: gợi ý từ gần đúng, gọi sau khi ngừng gõ 250 ms.
- `GET /search?q=...&limit=20&mode=contains`: tìm chuỗi khi nhấn nút Tìm hoặc Enter.
- `GET /dictionary?q=...&page=...&page_size=50`: lọc, sắp xếp và phân trang từ khóa.
- `GET /dictionary/stats`: thống kê từ điển, thuật toán và cache.
- `POST /benchmark/runs`: chạy benchmark với truy vấn mẫu, tùy chọn đối chiếu bản gốc.
- `GET /benchmark/runs/{run_id}/export`: tải kết quả benchmark dạng CSV.

Client nằm trong `src/services/searchService.ts`; URL gốc được lấy từ
`VITE_API_BASE_URL`.
