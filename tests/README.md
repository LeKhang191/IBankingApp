# Kiểm thử iBanking — đơn giản, tập trung nghiệp vụ

Hai thư mục chính:

- `automation/`: script test nghiệp vụ thanh toán/Saga + Outbox và kiểm thử hai giao dịch đồng thời với PostgreSQL.
- `e2e/`: test HTTP thật (OTP, thanh toán, lịch sử, email Mailpit, Saga/concurrency) chạy trong Docker E2E cách ly.

## 1. Workflow smoke (hệ thống chính đã chạy)

```powershell
.\tests\automation\test-workflow.ps1
```

Lệnh cũ `test-workflow.bat` vẫn hoạt động.

## 2. Concurrency database (tùy chọn)

Chỉ sử dụng database thử nghiệm có thể xóa, tuyệt đối không dùng database ứng dụng chính:

```powershell
$env:TEST_DATABASE_URL = 'postgresql://user:password@localhost:5432/disposable_test_db'
.\tests\automation\test-concurrency.ps1
```

## 3. End-to-End (môi trường riêng, Mailpit)

```powershell
.\tests\e2e\run-e2e.ps1 -Build
```

Hoặc:

```powershell
docker compose -f docker-compose.e2e.yml up -d --build
docker compose -f docker-compose.e2e.yml run --rm e2e-tests
```

Lưu ý: không trỏ E2E vào dữ liệu thật; script E2E có thể tạo/sửa dữ liệu.
