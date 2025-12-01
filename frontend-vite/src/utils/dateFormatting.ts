/**
 * Format a date string or Date object to a localized date string
 * @param date - Date string, Date object, or null/undefined
 * @param options - Intl.DateTimeFormatOptions for customization
 * @returns Formatted date string or "N/A" if date is invalid
 */
export function formatDate(
  date: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "N/A";
  
  try {
    const dateObj = typeof date === "string" ? new Date(date) : date;
    
    if (isNaN(dateObj.getTime())) {
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
  date: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "N/A";
  
  try {
    const dateObj = typeof date === "string" ? new Date(date) : date;
    
    if (isNaN(dateObj.getTime())) {
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

