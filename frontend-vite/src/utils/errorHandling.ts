/**
 * Extract error message from various error types
 * Handles Axios errors, standard Error objects, and unknown types
 */
export function extractErrorMessage(error: unknown, defaultMessage: string = "An error occurred"): string {
  if (error instanceof Error) {
    return error.message || defaultMessage;
  }
  
  // Handle Axios-like errors
  if (typeof error === "object" && error !== null) {
    const axiosError = error as { response?: { data?: { detail?: string; message?: string } }; message?: string };
    
    if (axiosError.response?.data?.detail) {
      return axiosError.response.data.detail;
    }
    
    if (axiosError.response?.data?.message) {
      return axiosError.response.data.message;
    }
    
    if (axiosError.message) {
      return axiosError.message;
    }
  }
  
  return defaultMessage;
}

/**
 * Type guard to check if error is an Axios-like error
 */
export function isAxiosError(error: unknown): error is { response?: { data?: { detail?: string } } } {
  return (
    typeof error === "object" &&
    error !== null &&
    "response" in error
  );
}

