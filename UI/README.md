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
`http://127.0.0.1:8000`. Có thể đặt `VITE_API_BASE_URL` để dùng địa chỉ backend
khác, ví dụ `VITE_API_BASE_URL=https://api.example.com`.

## API đang dùng

- `GET /search/suggest?q=...&limit=5`: gợi ý từ gần đúng, gọi sau khi ngừng gõ 250 ms.
- `GET /search?q=...&limit=20&mode=contains`: tìm chuỗi khi nhấn nút Tìm hoặc Enter.

Client nằm trong `src/services/searchService.ts`; URL gốc được lấy từ
`VITE_API_BASE_URL`.
