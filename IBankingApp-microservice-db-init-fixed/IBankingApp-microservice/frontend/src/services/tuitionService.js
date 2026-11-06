import axiosClient from './axiosClient'
import paymentService from './paymentService'

const tuitionClient = axiosClient

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
