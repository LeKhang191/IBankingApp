import axiosClient from './axiosClient';

const authService = {
  login: async (username, password) => {
    const response = await axiosClient.post('/api/auth/login', { username, password });
    return response.data; 
  },

  getMe: async () => {
    const response = await axiosClient.get('/api/auth/me');
    return response.data; 
  },

  logout: async () => {
    const response = await axiosClient.post('/api/auth/logout');
    return response.data; 
  }
};

export default authService;