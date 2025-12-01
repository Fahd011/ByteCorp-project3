/**
 * Default values constants for consistent fallback values across the application
 */
export const DEFAULT_VALUES = {
  PROVIDER: "Unknown",
  PROVIDER_FULL: "Unknown Provider",
  FILENAME: "unknown.pdf",
  BILLING_MONTH: "N/A",
  STATUS: "Unknown",
  ACCOUNT_EMAIL: "N/A",
} as const;

/**
 * Get default value for provider name
 */
export function getDefaultProvider(full: boolean = false): string {
  return full ? DEFAULT_VALUES.PROVIDER_FULL : DEFAULT_VALUES.PROVIDER;
}

/**
 * Get default value for filename
 */
export function getDefaultFilename(): string {
  return DEFAULT_VALUES.FILENAME;
}

/**
 * Get default value for billing month
 */
export function getDefaultBillingMonth(): string {
  return DEFAULT_VALUES.BILLING_MONTH;
}

