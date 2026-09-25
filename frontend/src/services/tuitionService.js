import axios from 'axios';

const tuitionClient = axios.create({
  baseURL: import.meta.env.VITE_TUITION_API_URL || 'http://localhost:8002'
});

tuitionClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

const tuitionService = {
  lookupTuition: async (mssv) => {
    const response = await tuitionClient.get(`/api/tuitions/${mssv}`);
    const data = response.data;
    
    return {
      mssv: data.student_code,
      studentName: data.student_name,
      amount: data.tuition_fee,
      isPaid: data.is_paid
    };
  },
  payTuition: async (mssv) => {
    const PAYMENT_API_URL = import.meta.env.VITE_PAYMENT_API_URL || 'http://localhost:8003';
    
    const response = await tuitionClient.post(`/api/tuitions/${mssv}/pay`);
    return response.data; 
  }
};

export default tuitionService;