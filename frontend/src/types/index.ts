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
  // New scheduling fields
  is_scheduled?: boolean;
  schedule_type?: "weekly" | "daily" | "monthly" | "custom";
  schedule_config?: {
    day_of_week?: number; // 0-6 (Sunday-Saturday)
    hour?: number; // 0-23
    minute?: number; // 0-59
    cron_expression?: string; // For custom scheduling
  };
  next_run?: string; // ISO string of next scheduled run
  last_scheduled_run?: string; // ISO string of last scheduled run
}

export interface JobResult {
  id: string;
  email: string;
  status: string;
  error?: string;
  filename?: string;
  file_url?: string;
  proxy_url?: string;
  retry_attempts?: number;
  final_error?: string;
  created_at?: string;
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
  // New scheduling fields
  is_scheduled?: boolean;
  schedule_type?: "weekly" | "daily" | "monthly" | "custom";
  schedule_config?: {
    day_of_week?: number;
    hour?: number;
    minute?: number;
    cron_expression?: string;
  };
}
