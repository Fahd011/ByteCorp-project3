import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (credentials) => api.post('/auth/login', credentials),
  register: (userData) => api.post('/auth/register', userData),
  createTestUser: () => api.post('/create-test-user'),
};

// Credentials API
export const credentialsAPI = {
  upload: (formData) => api.post('/credentials/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),
  getAll: () => api.get('/credentials'),
  uploadPDF: (credId, formData) => api.post(`/credentials/${credId}/upload_pdf`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),
  controlAgent: (credId, action) => api.post(`/credentials/${credId}/agent`, { action }),
  delete: (credId) => api.delete(`/credentials/${credId}`),
  downloadPDF: (credId) => api.get(`/credentials/${credId}/download_pdf`, { responseType: 'blob' }),
};

// Sessions API
export const sessionsAPI = {
  getAll: () => api.get('/sessions'),
  getResults: (sessionId) => api.get(`/results/${sessionId}`),
};

// Scheduling API
export const schedulingAPI = {
  scheduleWeekly: () => api.post('/schedule/weekly'),
};

// Health check
export const healthAPI = {
  check: () => api.get('/health'),
};

export default api;
