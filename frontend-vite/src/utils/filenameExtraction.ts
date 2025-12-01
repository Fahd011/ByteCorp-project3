/**
 * Extract filename from a blob path or URL
 * @param blobPath - The blob path or URL (e.g., "path/to/file.pdf" or "https://.../file.pdf")
 * @param fallback - Fallback filename if extraction fails
 * @returns The extracted filename
 */
export function extractFilename(blobPath: string | null | undefined, fallback: string = "download"): string {
  if (!blobPath) return fallback;
  
  // Handle both forward and backslashes
  const parts = blobPath.split(/[/\\]/);
  const filename = parts[parts.length - 1] || fallback;
  
  return filename;
}

/**
 * Extract filename without extension
 */
export function extractFilenameWithoutExtension(blobPath: string | null | undefined, fallback: string = "download"): string {
  const filename = extractFilename(blobPath, fallback);
  const lastDotIndex = filename.lastIndexOf(".");
  
  if (lastDotIndex === -1) return filename;
  return filename.substring(0, lastDotIndex);
}

/**
 * Extract file extension from blob path
 */
export function extractFileExtension(blobPath: string | null | undefined): string {
  if (!blobPath) return "";
  
  const filename = extractFilename(blobPath);
  const lastDotIndex = filename.lastIndexOf(".");
  
  if (lastDotIndex === -1) return "";
  return filename.substring(lastDotIndex + 1);
}

