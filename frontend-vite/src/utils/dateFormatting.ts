/**
 * Type alias for date input - can be a string, Date object, or null/undefined
 */
export type DateInput = string | Date | null | undefined;

/**
 * Parse a date string ensuring timezone awareness
 * If the string doesn't have timezone info, assume it's UTC
 */
function parseDate(date: string | Date): Date {
  if (date instanceof Date) {
    return date;
  }
  
  // If it's an ISO string without timezone, assume UTC
  // ISO strings like "2024-01-01T12:00:00" (no Z or offset) are treated as local time by Date constructor
  // We want to ensure UTC timestamps are properly recognized
  if (typeof date === "string") {
    const trimmed = date.trim();
    // If it ends with Z or has timezone offset (+/-HH:MM), Date will parse it correctly
    // If it doesn't, we'll append Z to treat it as UTC
    if (trimmed && !trimmed.endsWith('Z') && !trimmed.match(/[+-]\d{2}:\d{2}$/)) {
      // No timezone info - assume UTC if it looks like an ISO datetime
      if (trimmed.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)) {
        return new Date(trimmed + 'Z');
      }
    }
  }
  
  return new Date(date);
}

/**
 * Format a date string or Date object to a localized date string
 * @param date - Date string, Date object, or null/undefined
 * @param options - Intl.DateTimeFormatOptions for customization
 * @returns Formatted date string or "N/A" if date is invalid
 */
export function formatDate(
  date: DateInput,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "N/A";
  
  try {
    const dateObj = parseDate(date);
    
    if (Number.isNaN(dateObj.getTime())) {
      return "N/A";
    }
    
    return dateObj.toLocaleDateString(undefined, options);
  } catch {
    return "N/A";
  }
}

/**
 * Format a date to a full date-time string
 */
export function formatDateTime(
  date: DateInput,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "N/A";
  
  try {
    const dateObj = parseDate(date);
    
    if (Number.isNaN(dateObj.getTime())) {
      return "N/A";
    }
    
    return dateObj.toLocaleString(undefined, options);
  } catch {
    return "N/A";
  }
}

/**
 * Format billing month and year
 */
export function formatBillingMonth(month: string | null | undefined, year: string | null | undefined): string {
  if (!month || !year) return "N/A";
  return `${month} ${year}`;
}

/**
 * Format time only (HH:MM:SS)
 * Uses browser's local timezone for display
 */
export function formatTime(
  date: DateInput
): string {
  if (!date) return "—";
  
  try {
    const dateObj = parseDate(date);
    
    if (Number.isNaN(dateObj.getTime())) {
      return "—";
    }
    
    return dateObj.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "—";
  }
}

