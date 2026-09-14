# iBanking Frontend

Frontend cho phân hệ đóng học phí của ứng dụng iBanking. Xây bằng **React + Vite + TailwindCSS**.

## Cài đặt & chạy

```bash
cd frontend
npm install
npm run dev
```

Mở trình duyệt tại `http://localhost:5173`.

**Tài khoản demo:**
| Username | Password | Ghi chú |
|----------|----------|---------|
| sv001    | 123456   | Số dư 12.000.000đ |
| sv002    | 123456   | Số dư 3.000.000đ (đủ test trường hợp không đủ số dư) |

**MSSV demo để tra cứu học phí:**
- `52100001`, `52100002`, `52100003` — chưa đóng
- `52100004` — đã đóng (test trường hợp không cho thanh toán lại)

## Cấu trúc thư mục

```
src/
  components/     UI dùng chung (layout, step indicator, ô nhập OTP...)
  context/        AuthContext (phiên đăng nhập), PaymentFlowContext (state 3 bước thanh toán)
  pages/          Từng trang / route
  services/mockApi.js   Lớp giả lập 4 backend service, xem chi tiết bên dưới
```

## Về `services/mockApi.js`

File này **giả lập toàn bộ backend** (auth-service, tuition-service, payment-service,
notification-service) bằng dữ liệu trong bộ nhớ, để phần frontend có thể chạy độc lập
trong lúc backend đang được xây dựng song song.

Mỗi hàm export (`login`, `lookupTuition`, `createPaymentRequest`, `verifyOtp`,
`getHistory`,...) có input/output được thiết kế giống hệt một API thật sẽ trả về.
**Khi backend đã sẵn sàng, chỉ cần sửa bên trong các hàm này để gọi `fetch`/`axios`
tới API thật** — không cần đổi bất kỳ page hay component nào đang import từ file này.

Gợi ý endpoint REST tương ứng để 2 bạn thống nhất khi build backend thật:

| Hàm mock                          | Method | Endpoint gợi ý                          |
|-----------------------------------|--------|------------------------------------------|
| `login`                           | POST   | `/api/auth/login`                        |
| `getCurrentUser`                  | GET    | `/api/auth/me`                           |
| `lookupTuition`                   | GET    | `/api/tuition/{mssv}`                    |
| `createPaymentRequest`            | POST   | `/api/payments`                          |
| `resendOtp`                       | POST   | `/api/payments/{transactionId}/otp/resend` |
| `verifyOtp`                       | POST   | `/api/payments/{transactionId}/otp/verify` |
| `getHistory`                      | GET    | `/api/payments/history`                  |

Lưu ý quan trọng cho backend (mục 5 & 6 của đề bài — concurrency/transaction):
- `createPaymentRequest` phải khoá khoản học phí (unique lock theo MSSV) ngay khi tạo
  yêu cầu, để 2 người không thể cùng lúc thanh toán 1 MSSV.
- `verifyOtp` phải chạy trong 1 DB transaction: kiểm tra lại số dư + trạng thái học phí,
  trừ tiền, cập nhật học phí thành "đã thanh toán", ghi lịch sử — tất cả hoặc không có gì
  (atomic), để tránh trừ tiền nhưng không cập nhật học phí (hoặc ngược lại).
- OTP chỉ được dùng 1 lần, hết hạn sau 5 phút, không được trả OTP thật về response
  (mock đang trả `__devOtp` chỉ để demo khi chưa nối email thật — phải bỏ ở bản thật).
