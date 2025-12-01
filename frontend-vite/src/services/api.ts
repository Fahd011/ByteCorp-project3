import axios, {
  AxiosResponse,
  AxiosError,
  InternalAxiosRequestConfig,
} from "axios";
import {
  Token,
  UserBillingCredential,
  LoginCredentials,
  RegisterData,
  AgentAction,
  Provider,
  ManualBill,
  BillingResult,
  ExtractionResult,
  TestUserResponse,
  HealthCheckResponse,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem("token");
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
      localStorage.removeItem("token");
      globalThis.location.href = "/auth";
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (credentials: LoginCredentials): Promise<AxiosResponse<Token>> =>
    api.post("/auth/login", credentials),
  register: (userData: RegisterData): Promise<AxiosResponse<Token>> =>
    api.post("/auth/register", userData),
  createTestUser: (): Promise<AxiosResponse<TestUserResponse>> =>
    api.post("/create-test-user"),
};

// Provider API
export const providerAPI = {
  getAll: (): Promise<AxiosResponse<Provider[]>> => api.get("/providers"),
  getById: (providerId: string): Promise<AxiosResponse<Provider>> =>
    api.get(`/providers/${providerId}`),
};

// Credentials API
export const credentialsAPI = {
  upload: (formData: FormData): Promise<AxiosResponse<{ message: string }>> =>
    api.post("/credentials/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }),
  getAll: (): Promise<AxiosResponse<UserBillingCredential[]>> =>
    api.get("/credentials"),
  uploadPDF: (
    credId: string,
    formData: FormData
  ): Promise<AxiosResponse<{ message: string }>> =>
    api.post(`/credentials/${credId}/upload_pdf`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }),
  controlAgent: (
    credId: string,
    action: AgentAction
  ): Promise<AxiosResponse<{ message: string }>> =>
    api.post(`/credentials/${credId}/agent`, { action }),
  delete: (credId: string): Promise<AxiosResponse<{ message: string }>> =>
    api.delete(`/credentials/${credId}`),

  getBillingResults: (credId: string): Promise<AxiosResponse<BillingResult[]>> =>
    api.get(`/billing-results/${credId}`),
  getAllBillingResults: (): Promise<AxiosResponse<BillingResult[]>> =>
    api.get(`/billing-results`),

  downloadPDF: (blobName: string): Promise<AxiosResponse<Blob>> =>
    api.get(`/azure/download/${encodeURIComponent(blobName)}`, {
      responseType: "blob",
    }),

  // Manual credential PDF upload
  uploadManualPDF: (
    credId: string,
    formData: FormData
  ): Promise<AxiosResponse<{ message: string }>> =>
    api.post(`/credentials/${credId}/upload_pdf`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }),

  downloadExcel: (blobName: string): Promise<AxiosResponse<Blob>> =>
    api.get(`/azure/download/${encodeURIComponent(blobName)}`, {
      responseType: "blob",
    }),

  downloadJSON: (blobName: string): Promise<AxiosResponse<Blob>> =>
    api.get(`/azure/download/${encodeURIComponent(blobName)}`, {
      responseType: "blob",
    }),
};

// PDF Extraction API
export const pdfExtractionAPI = {
  extractData: (billingResult: BillingResult): Promise<AxiosResponse<{ session_id: string; message: string }>> =>
    api.post("/pdf-extraction/upload", {
      billing_result: billingResult,
    }),
  getResults: (sessionId: string): Promise<AxiosResponse<{ results: ExtractionResult[] }>> =>
    api.get(`/pdf-extraction/results/${sessionId}`),
  exportToExcel: (sessionId: string): Promise<AxiosResponse<Blob>> =>
    api.get(`/pdf-extraction/export/${sessionId}`, {
      responseType: "blob",
    }),
};

// Removed sessionsAPI - no longer needed

// Scheduling API
export const schedulingAPI = {
  scheduleWeekly: (): Promise<AxiosResponse<{ message: string }>> =>
    api.post("/schedule/weekly"),
};

// Manual Bills API
export const manualBillsAPI = {
  upload: (formData: FormData): Promise<AxiosResponse<ManualBill>> =>
    api.post("/manual-bills/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }),
  bulkUpload: (formData: FormData): Promise<AxiosResponse<{ message: string; count: number }>> =>
    api.post("/manual-bills/bulk-upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }),
  getAll: (): Promise<AxiosResponse<ManualBill[]>> => api.get("/manual-bills"),
  downloadPDF: (blobName: string): Promise<AxiosResponse<Blob>> =>
    api.get(`/azure/download/${encodeURIComponent(blobName)}`, {
      responseType: "blob",
    }),
  downloadExcel: (blobName: string): Promise<AxiosResponse<Blob>> =>
    api.get(`/azure/download/${encodeURIComponent(blobName)}`, {
      responseType: "blob",
    }),
  downloadJSON: (blobName: string): Promise<AxiosResponse<Blob>> =>
    api.get(`/azure/download/${encodeURIComponent(blobName)}`, {
      responseType: "blob",
    }),
};

// Audit logs API
export const auditLogsAPI = {
  downloadCSV: (): Promise<AxiosResponse<Blob>> =>
    api.get("/audit-logs/download", {
      responseType: "blob",
    }),
};

// Health check
export const healthAPI = {
  check: (): Promise<AxiosResponse<HealthCheckResponse>> => api.get("/health"),
};

export default api;

