// Type definitions for API interactions

export interface Token {
  access_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
}

export interface AgentAction {
  action: "RUN" | "STOPPED";
}

export interface UserBillingCredential {
  id: string;
  email: string;
  client_name?: string | null;
  utility_co_id?: string | null;
  utility_co_name?: string | null;
  cred_id?: string | null;
  login_url?: string | null;
  billing_url?: string | null;
  billing_cycle_day?: number | null;
  is_active: boolean;
  is_deleted: boolean;
  last_state: string;
  last_error?: string | null;
  is_eligible_for_retry: boolean;
  last_run_time?: string | null;
  uploaded_bill_url?: string | null;
  created_at: string;
}

export interface Provider {
  id: string;
  name: string;
  login_url: string;
  billing_url: string;
  extras?: Record<string, unknown> | null;
  created_at: string;
}

export interface ManualBill {
  id: string;
  original_filename?: string | null;
  provider_name?: string | null;
  azure_blob_url: string;
  excel_blob_url?: string | null;
  json_blob_url?: string | null;
  status: string;
  year: string;
  month: string;
  created_at: string;
  login_url?: string | null;
}

export interface BillingResult {
  id: string;
  azure_blob_url: string;
  excel_blob_url?: string | null;
  json_blob_url?: string | null;
  run_time: string;
  status: string;
  year: string;
  month: string;
  created_at: string;
  username: string;
  account_number?: string | null;
}

export interface ExtractionResult {
  filename: string;
  extracted_data: Record<string, unknown>;
  status: string;
  error?: string | null;
}

export interface TestUserResponse {
  id: string;
  email: string;
  message?: string;
}

export interface HealthCheckResponse {
  status: string;
}

export interface ApiResponse<T = unknown> {
  data: T;
  message?: string;
}

export interface User {
  email: string;
}

