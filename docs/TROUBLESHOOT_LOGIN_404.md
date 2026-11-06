# Kiểm tra lỗi login 404 trên frontend

Source hiện tại **đã đồng nhất** các đường dẫn: frontend POST `/api/auth/login`, FastAPI khai báo `/api/auth/login`, nginx `location /api/auth/` chuyển tiếp sang `auth-service:8001` **không cắt prefix**.

Nếu máy bạn vẫn thấy `404`, đó là dấu hiệu container/config đang chạy chưa giống source hoặc request đã bị chuyển đến một hệ thống khác. Không đổi bừa endpoint thành `/login`.

1. Mở PowerShell **ở đúng thư mục gốc** chứa `docker-compose.yml` và `gateway/nginx.conf`.
2. Chạy `docker compose ps` để đảm bảo `api-gateway` chạy và có mapping `8080:80`.
3. Chạy `docker compose exec api-gateway nginx -T` để xem cấu hình nginx **đang chạy**, không phải file được mở trong VS Code.
4. Chạy `curl.exe -i -X POST http://localhost:8080/api/auth/login -H "Content-Type: application/json" --data-raw '{"username":"invalid","password":"invalid"}'`. Kết quả đúng là **401** (tài khoản sai), không phải **404**.
5. Nếu vẫn 404: `docker compose up -d --force-recreate api-gateway`, rồi lặp lại bước 4.
6. Nếu gateway trả 401 nhưng frontend vẫn 404: mở DevTools > Network > login > xem Request URL và Request Method, đảm bảo `http://localhost:8080/api/auth/login` và POST; kiểm tra `frontend/.env*`, `VITE_API_URL`, rebuild frontend nếu cần.
7. Nếu Gateway trả 404, so sánh với `docker compose exec auth-service python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/openapi.json').status)"` và tìm `/api/auth/login` trong OpenAPI docs.

**Lưu ý:** `404` là lỗi đường dẫn / proxy, khác với `401` (mật khẩu sai) và `503` (service chưa sẵn sàng). Hai Docker Compose project `docker-compose.yml` (8080/5173) và `docker-compose.e2e.yml` (18080/15173) chạy trên các cổng khác nhau.
