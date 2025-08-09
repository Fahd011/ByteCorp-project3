export interface User {
  id: string;
  email: string;
}

export interface Job {
  id: string;
  csv_url: string;
  login_url: string;
  billing_url: string;
  status: "idle" | "running" | "completed" | "stopped" | "error";
  created_at: string;
  results_count: number;
}

export interface JobResult {
  id: string;
  email: string;
  status: string;
  error?: string;
  filename?: string;
  file_url?: string;
}

export interface JobDetail extends Job {
  output: JobResult[];
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  expires_at: string;
  user: User;
}

export interface CreateJobData {
  csv: File;
  login_url: string;
  billing_url: string;
}
