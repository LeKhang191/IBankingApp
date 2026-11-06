/**
 * MOCK API LAYER
 * ---------------
 * File này giả lập 4 backend service được mô tả trong đề bài:
 *   - auth-service         -> login, getCurrentUser
 *   - tuition-service      -> lookupTuition
 *   - payment-service      -> createPaymentRequest, verifyOtp, getHistory
 *   - notification-service -> gửi OTP qua email (ở đây log ra console + trả
 *                              kèm trong response để demo, KHÔNG làm vậy ở backend thật)
 *
 * Mục tiêu: mọi hàm export bên dưới có "chữ ký" (tham số đầu vào / dữ liệu trả
 * về) giống hệt những gì frontend cần từ REST API thật. Khi bạn của bạn code
 * xong backend, chỉ cần thay phần "giả lập" bên trong mỗi hàm bằng:
 *
 *   const res = await fetch(`${BASE_URL}/...`, { method, headers, body })
 *   if (!res.ok) throw new ApiError(...)
 *   return res.json()
 *
 * mà KHÔNG cần sửa bất kỳ page/component nào đang gọi các hàm này.
 */

// ----------------------- Cấu hình & tiện ích -----------------------

const NETWORK_DELAY_MS = 500

function delay(ms = NETWORK_DELAY_MS) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export class ApiError extends Error {
  constructor(message, code = 'UNKNOWN_ERROR', status = 400) {
    super(message)
    this.code = code
    this.status = status
  }
}

function genId(prefix) {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 100000)}`
}

function genOtp() {
  return String(Math.floor(100000 + Math.random() * 900000))
}

function formatVnd(n) {
  return n.toLocaleString('vi-VN') + ' đ'
}

// ----------------------- "Cơ sở dữ liệu" giả lập -----------------------

const db = {
  users: [
    {
      id: 'u1',
      username: 'sv001',
      password: '123456',
      name: 'Nguyễn Văn An',
      phone: '0901234567',
      email: 'an.nguyen@student.tdtu.edu.vn',
      balance: 12000000
    },
    {
      id: 'u2',
      username: 'sv002',
      password: '123456',
      name: 'Trần Thị Bích',
      phone: '0912345678',
      email: 'bich.tran@student.tdtu.edu.vn',
      balance: 3000000
    }
  ],

  // Khoản học phí của sinh viên (người nộp có thể đóng hộ MSSV khác)
  tuitions: [
    { mssv: '52100001', studentName: 'Nguyễn Văn An', amount: 8500000, status: 'unpaid' },
    { mssv: '52100002', studentName: 'Trần Thị Bích', amount: 6200000, status: 'unpaid' },
    { mssv: '52100003', studentName: 'Lê Hoàng Cường', amount: 10450000, status: 'unpaid' },
    { mssv: '52100004', studentName: 'Phạm Thu Dung', amount: 7300000, status: 'paid' }
  ],

  // Lịch sử giao dịch, key theo userId
  transactionsByUser: {
    u1: [],
    u2: []
  },

  // Giao dịch đang chờ xác thực OTP: transactionId -> { ...info }
  pendingTransactions: new Map(),

  // Khoá các MSSV đang được thanh toán để mô phỏng yêu cầu #5 (concurrency):
  // "nhiều tài khoản cùng thanh toán 1 MSSV" phải chỉ có 1 giao dịch thành công.
  lockedMssv: new Set()
}

let currentToken = null

function requireAuth(token) {
  const session = sessions.get(token)
  if (!session) {
    throw new ApiError('Phiên đăng nhập không hợp lệ hoặc đã hết hạn.', 'UNAUTHORIZED', 401)
  }
  return session
}

const sessions = new Map() // token -> userId

// ----------------------- 1. auth-service -----------------------

export async function login(username, password) {
  await delay()
  const user = db.users.find((u) => u.username === username)
  if (!user || user.password !== password) {
    throw new ApiError('Sai tên đăng nhập hoặc mật khẩu.', 'INVALID_CREDENTIALS', 401)
  }
  const token = genId('token')
  sessions.set(token, user.id)
  return {
    token,
    user: sanitizeUser(user)
  }
}

export async function logout(token) {
  await delay(150)
  sessions.delete(token)
  return { success: true }
}

export async function getCurrentUser(token) {
  await delay(250)
  const session = requireAuth(token)
  const user = db.users.find((u) => u.id === session)
  return sanitizeUser(user)
}

function sanitizeUser(user) {
  const { password, ...rest } = user
  return rest
}

// ----------------------- 2. tuition-service -----------------------

export async function lookupTuition(token, mssv) {
  await delay()
  requireAuth(token)
  const record = db.tuitions.find((t) => t.mssv === mssv)
  if (!record) {
    throw new ApiError('Không tìm thấy sinh viên với MSSV này.', 'STUDENT_NOT_FOUND', 404)
  }
  if (record.status === 'paid') {
    throw new ApiError('Khoản học phí này đã được thanh toán.', 'ALREADY_PAID', 409)
  }
  if (db.lockedMssv.has(mssv)) {
    throw new ApiError(
      'Khoản học phí này đang được một giao dịch khác xử lý, vui lòng thử lại sau ít phút.',
      'TUITION_LOCKED',
      409
    )
  }
  return { ...record }
}

// ----------------------- 3. payment-service -----------------------

/**
 * Bước xác nhận giao dịch: kiểm tra số dư + khoá MSSV + tạo OTP.
 * payload: { mssv }
 */
export async function createPaymentRequest(token, { mssv }) {
  await delay()
  const session = requireAuth(token)
  const payer = db.users.find((u) => u.id === session)
  const tuition = db.tuitions.find((t) => t.mssv === mssv)

  if (!tuition) throw new ApiError('Không tìm thấy khoản học phí.', 'STUDENT_NOT_FOUND', 404)
  if (tuition.status === 'paid') {
    throw new ApiError('Khoản học phí này đã được thanh toán.', 'ALREADY_PAID', 409)
  }
  if (db.lockedMssv.has(mssv)) {
    throw new ApiError(
      'Khoản học phí này đang được xử lý bởi một giao dịch khác.',
      'TUITION_LOCKED',
      409
    )
  }
  if (payer.balance < tuition.amount) {
    throw new ApiError('Số dư khả dụng không đủ để thanh toán.', 'INSUFFICIENT_BALANCE', 400)
  }

  // Khoá MSSV lại: giao dịch khác (kể cả tài khoản khác) không thể tạo
  // request mới cho cùng MSSV này cho đến khi giao dịch hiện tại kết thúc
  // (thành công / thất bại / hết hạn OTP). Backend thật nên dùng
  // SELECT ... FOR UPDATE hoặc unique constraint + transaction DB.
  db.lockedMssv.add(mssv)

  const transactionId = genId('txn')
  const otp = genOtp()
  const expiresAt = Date.now() + 5 * 60 * 1000 // 5 phút

  db.pendingTransactions.set(transactionId, {
    transactionId,
    payerId: payer.id,
    mssv,
    studentName: tuition.studentName,
    amount: tuition.amount,
    otp,
    expiresAt,
    used: false,
    attempts: 0
  })

  // notification-service: gửi OTP qua email (ở đây chỉ log ra console)
  // eslint-disable-next-line no-console
  console.info(`[notification-service] Gửi OTP ${otp} đến ${payer.email} (demo, hết hạn sau 5 phút)`)

  return {
    transactionId,
    otpSentTo: maskEmail(payer.email),
    expiresAt,
    // CHỈ dùng để demo không có email thật — backend thật KHÔNG được trả otp về client
    __devOtp: otp
  }
}

export async function resendOtp(token, transactionId) {
  await delay(400)
  requireAuth(token)
  const txn = db.pendingTransactions.get(transactionId)
  if (!txn || txn.used) {
    throw new ApiError('Giao dịch không tồn tại hoặc đã xử lý xong.', 'TXN_NOT_FOUND', 404)
  }
  txn.otp = genOtp()
  txn.expiresAt = Date.now() + 5 * 60 * 1000
  txn.attempts = 0
  // eslint-disable-next-line no-console
  console.info(`[notification-service] Gửi lại OTP ${txn.otp} cho giao dịch ${transactionId}`)
  return { transactionId, expiresAt: txn.expiresAt, __devOtp: txn.otp }
}

export async function verifyOtp(token, transactionId, otp) {
  await delay()
  const session = requireAuth(token)
  const txn = db.pendingTransactions.get(transactionId)

  if (!txn || txn.payerId !== session) {
    throw new ApiError('Giao dịch không tồn tại.', 'TXN_NOT_FOUND', 404)
  }
  if (txn.used) {
    throw new ApiError('Mã OTP này đã được sử dụng.', 'OTP_USED', 409)
  }
  if (Date.now() > txn.expiresAt) {
    db.lockedMssv.delete(txn.mssv)
    db.pendingTransactions.delete(transactionId)
    throw new ApiError('Mã OTP đã hết hạn. Vui lòng thực hiện lại giao dịch.', 'OTP_EXPIRED', 410)
  }
  txn.attempts += 1
  if (txn.otp !== otp) {
    if (txn.attempts >= 5) {
      db.lockedMssv.delete(txn.mssv)
      db.pendingTransactions.delete(transactionId)
      throw new ApiError('Sai OTP quá số lần cho phép. Giao dịch đã bị huỷ.', 'OTP_MAX_ATTEMPTS', 429)
    }
    throw new ApiError('Mã OTP không đúng.', 'OTP_INVALID', 400)
  }

  // ----- Vùng "transaction" trên backend thật: các thao tác dưới đây phải
  // atomic (cùng 1 DB transaction) để đảm bảo tính nhất quán yêu cầu #5 -----
  const payer = db.users.find((u) => u.id === txn.payerId)
  const tuition = db.tuitions.find((t) => t.mssv === txn.mssv)

  if (payer.balance < txn.amount || tuition.status === 'paid') {
    // Trường hợp hiếm: dữ liệu đổi giữa lúc nhập OTP (ví dụ giao dịch khác
    // đã trừ tiền học phí này trước). Phải rollback toàn bộ.
    db.lockedMssv.delete(txn.mssv)
    db.pendingTransactions.delete(transactionId)
    throw new ApiError('Giao dịch không còn hợp lệ, vui lòng thử lại.', 'TXN_CONFLICT', 409)
  }

  payer.balance -= txn.amount
  tuition.status = 'paid'
  txn.used = true

  const record = {
    id: transactionId,
    mssv: txn.mssv,
    studentName: txn.studentName,
    amount: txn.amount,
    status: 'success',
    createdAt: new Date().toISOString()
  }
  if (!db.transactionsByUser[payer.id]) db.transactionsByUser[payer.id] = []
  db.transactionsByUser[payer.id].unshift(record)

  db.lockedMssv.delete(txn.mssv)
  db.pendingTransactions.delete(transactionId)
  // ----- kết thúc vùng transaction -----

  // eslint-disable-next-line no-console
  console.info(`[notification-service] Gửi email xác nhận giao dịch ${transactionId} thành công`)

  return {
    ...record,
    payerBalanceAfter: payer.balance
  }
}

export async function getHistory(token) {
  await delay(300)
  const session = requireAuth(token)
  return db.transactionsByUser[session] || []
}

export { formatVnd, maskEmail }

function maskEmail(email) {
  const [name, domain] = email.split('@')
  if (name.length <= 2) return `${name[0]}***@${domain}`
  return `${name.slice(0, 2)}${'*'.repeat(Math.max(name.length - 2, 3))}@${domain}`
}
