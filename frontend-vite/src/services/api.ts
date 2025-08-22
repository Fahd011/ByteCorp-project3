import axios, { AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { 
  Token, 
  UserBillingCredential, 
  ImportSession, 
  ImportResult, 
  LoginCredentials, 
  RegisterData,
  AgentAction 
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (credentials: LoginCredentials): Promise<AxiosResponse<Token>> => 
    api.post('/auth/login', credentials),
  register: (userData: RegisterData): Promise<AxiosResponse<Token>> => 
    api.post('/auth/register', userData),
  createTestUser: (): Promise<AxiosResponse<any>> => 
    api.post('/create-test-user'),
};

// Credentials API
export const credentialsAPI = {
  upload: (formData: FormData): Promise<AxiosResponse<any>> => 
    api.post('/credentials/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  getAll: (): Promise<AxiosResponse<UserBillingCredential[]>> => 
    api.get('/credentials'),
  uploadPDF: (credId: string, formData: FormData): Promise<AxiosResponse<any>> => 
    api.post(`/credentials/${credId}/upload_pdf`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  controlAgent: (credId: string, action: AgentAction): Promise<AxiosResponse<any>> => 
    api.post(`/credentials/${credId}/agent`, { action }),
  delete: (credId: string): Promise<AxiosResponse<any>> => 
    api.delete(`/credentials/${credId}`),
  downloadPDF: (credId: string): Promise<AxiosResponse<Blob>> => 
    api.get(`/credentials/${credId}/download_pdf`, { responseType: 'blob' }),
};

// Sessions API
export const sessionsAPI = {
  getAll: (): Promise<AxiosResponse<ImportSession[]>> => 
    api.get('/sessions'),
  getResults: (sessionId: string): Promise<AxiosResponse<ImportResult[]>> => 
    api.get(`/results/${sessionId}`),
};

// Scheduling API
export const schedulingAPI = {
  scheduleWeekly: (): Promise<AxiosResponse<any>> => 
    api.post('/schedule/weekly'),
};

// Health check
export const healthAPI = {
  check: (): Promise<AxiosResponse<any>> => 
    api.get('/health'),
};

export default api;
