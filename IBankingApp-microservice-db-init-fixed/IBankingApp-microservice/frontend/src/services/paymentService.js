import axiosClient from './axiosClient'

const paymentClient = axiosClient

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
