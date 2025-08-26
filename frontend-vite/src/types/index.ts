// API Response Types
export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface UserBillingCredential {
  id: string;
  email: string;
  client_name?: string;
  utility_co_id?: string;
  utility_co_name?: string;
  cred_id?: string;
  login_url?: string;
  billing_url?: string;
  is_deleted: boolean;
  last_state: string;
  last_error?: string;
  last_run_time?: string;
  uploaded_bill_url?: string;
  created_at: string;
}

// Removed ImportSession - no longer needed

// Removed ImportResult - no longer needed

// Auth Types
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
}

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<{ success: boolean; error?: string }>;
  register: (userData: RegisterData) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  createTestUser: () => Promise<{ success: boolean; data?: any; error?: string }>;
}

// API Response Types
export interface ApiResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
}

export interface ErrorResponse {
  detail: string;
  status_code?: number;
}

// Form Types
export interface CredentialUploadForm {
  csv_file: File;
  login_url: string;
  billing_url: string;
}

export interface AgentAction {
  action: 'RUN' | 'STOPPED';
}
