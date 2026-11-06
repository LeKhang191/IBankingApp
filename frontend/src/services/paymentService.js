import axios from 'axios'

const paymentClient = axios.create({
  baseURL: import.meta.env.VITE_PAYMENT_API_URL || 'http://localhost:8003',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

paymentClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  if (token) config.headers.Authorization = token.startsWith('Bearer ') ? token : `Bearer ${token}`
  return config
})

const paymentService = {
  initPayment: (mssv) => paymentClient.post('/api/payments/init', { mssv }),
  resendOtp: (transactionId) => paymentClient.post(`/api/payments/resend-otp/${encodeURIComponent(transactionId)}`),
  verifyOtp: (transactionId, otp) => paymentClient.post('/api/payments/verify-otp', {
    transaction_id: transactionId,
    otp,
  }),
  getStatus: (transactionId) => paymentClient.get(`/api/payments/status/${encodeURIComponent(transactionId)}`),
  retryPayment: (transactionId) => paymentClient.post(`/api/payments/retry/${encodeURIComponent(transactionId)}`),
  getHistory: async () => (await paymentClient.get('/api/payments/history')).data,
}

export default paymentService
