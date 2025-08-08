import axios from 'axios';
import { LoginCredentials, AuthResponse, Job, CreateJobData } from '../types';

const API_BASE_URL = 'http://127.0.0.1:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  console.log('=== API REQUEST INTERCEPTOR ===');
  console.log('URL:', config.url);
  console.log('Method:', config.method);
  console.log('Token exists:', !!token);
  console.log('Token value:', token ? token.substring(0, 20) + '...' : 'null');
  
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    console.log('Authorization header set');
  } else {
    console.log('No token found - request will fail with 401');
  }
  
  console.log('Final headers:', config.headers);
  return config;
});

// Add response interceptor for debugging and handling auth errors
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.data);
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.status, error.response?.data);
    
    // Handle 401 Unauthorized errors
    if (error.response?.status === 401) {
      // Clear invalid token and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('tokenExpiresAt');
      localStorage.removeItem('user');
      
      // Redirect to login page if not already there
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await api.post('/auth/login', credentials);
    return response.data;
  },

  signup: async (credentials: LoginCredentials): Promise<{ message: string }> => {
    const response = await api.post('/auth/signup', credentials);
    return response.data;
  },
};

export const jobsAPI = {
  getAllJobs: async (): Promise<Job[]> => {
    const response = await api.get('/api/jobs');
    return response.data;
  },

  getJob: async (jobId: string): Promise<Job> => {
    const response = await api.get(`/api/jobs/${jobId}`);
    return response.data;
  },

  getJobDetails: async (jobId: string): Promise<any> => {
    const response = await api.get(`/api/jobs/${jobId}/details`);
    return response.data;
  },

  createJob: async (jobData: CreateJobData): Promise<Job> => {
    const formData = new FormData();
    formData.append('csv', jobData.csv);
    formData.append('login_url', jobData.login_url);
    formData.append('billing_url', jobData.billing_url);

    const response = await api.post('/api/jobs', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  runJob: async (jobId: string): Promise<Job> => {
    console.log('=== JOBS API RUN JOB CALLED ===');
    console.log('JobId:', jobId);
    console.log('API URL:', `${API_BASE_URL}/api/jobs/${jobId}/run`);
    console.log('Token from localStorage:', localStorage.getItem('token'));
    
    try {
      const response = await api.post(`/api/jobs/${jobId}/run`);
      console.log('runJob API call successful');
      console.log('Response status:', response.status);
      console.log('Response data:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('=== RUN JOB API ERROR ===');
      console.error('Error:', error);
      console.error('Error response:', (error as any).response);
      console.error('Error status:', (error as any).response?.status);
      console.error('Error data:', (error as any).response?.data);
      throw error;
    }
  },

  stopJob: async (jobId: string): Promise<Job> => {
    const response = await api.post(`/api/jobs/${jobId}/stop`);
    return response.data;
  },

  deleteJob: async (jobId: string): Promise<{ message: string }> => {
    const response = await api.delete(`/api/jobs/${jobId}`);
    return response.data;
  },

  deleteAllResults: async (jobId: string): Promise<{ message: string; deleted_count: number }> => {
    const response = await api.delete(`/api/jobs/${jobId}/results`);
    return response.data;
  },

  deleteSingleResult: async (jobId: string, resultId: string): Promise<{ message: string; deleted_result_id: string }> => {
    const response = await api.delete(`/api/jobs/${jobId}/results/${resultId}`);
    return response.data;
  },

  getJobCredentials: async (jobId: string): Promise<{ csv_url: string; filename: string }> => {
    const response = await api.get(`/api/jobs/${jobId}/credentials`);
    return response.data;
  },
};
