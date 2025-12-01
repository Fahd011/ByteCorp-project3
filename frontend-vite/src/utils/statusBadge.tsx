import { Badge } from "@/components/ui/badge";

export type StatusType = 
  | "idle" 
  | "active" 
  | "failed" 
  | "completed" 
  | "processing" 
  | "error" 
  | "running";

// Status color mapping - centralized for consistency
const STATUS_COLORS: Record<string, string> = {
  // Provider statuses
  idle: "bg-muted text-muted-foreground border-border",
  active: "bg-success/10 text-success border-success/20",
  running: "bg-success/10 text-success border-success/20", // Alias for active
  failed: "bg-destructive/10 text-destructive border-destructive/20",
  error: "bg-destructive/10 text-destructive border-destructive/20", // Alias for failed
  completed: "bg-primary/10 text-primary border-primary/20",
  
  // Billing result statuses
  processing: "bg-warning/10 text-warning border-warning/20",
};

/**
 * Get status badge component with consistent styling
 * @param status - The status value (will be lowercased for matching)
 * @param capitalize - Whether to capitalize the status text (default: true)
 * @returns Badge component with appropriate styling
 */
export function getStatusBadge(
  status: string | null | undefined,
  capitalize: boolean = true
) {
  const statusLower = status?.toLowerCase() || "";
  const colorClass = STATUS_COLORS[statusLower] || "bg-muted text-muted-foreground border-border";
  
  let displayText = status || "Unknown";
  if (capitalize && displayText) {
    displayText = displayText.charAt(0).toUpperCase() + displayText.slice(1);
  }
  
  return (
    <Badge variant="outline" className={colorClass}>
      {displayText}
    </Badge>
  );
}

/**
 * Get status color class only (for use in other components)
 */
export function getStatusColorClass(status: string | null | undefined): string {
  const statusLower = status?.toLowerCase() || "";
  return STATUS_COLORS[statusLower] || "bg-muted text-muted-foreground border-border";
}

