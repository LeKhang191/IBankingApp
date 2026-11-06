import axios from 'axios'
import paymentService from './paymentService'

const tuitionClient = axios.create({
  baseURL: import.meta.env.VITE_TUITION_API_URL || 'http://localhost:8002',
  timeout: 10000,
})

tuitionClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  if (token) config.headers.Authorization = token.startsWith('Bearer ') ? token : `Bearer ${token}`
  return config
})

const tuitionService = {
  lookupTuition: async (mssv) => {
    const { data } = await tuitionClient.get(`/api/tuitions/${encodeURIComponent(mssv)}`)
    return {
      mssv: data.student_code,
      studentName: data.student_name,
      amount: Number(data.tuition_fee),
      isPaid: data.is_paid,
    }
  },
  getHistory: () => paymentService.getHistory(),
}

export default tuitionService
