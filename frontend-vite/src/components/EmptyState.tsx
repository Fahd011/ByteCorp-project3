import { ReactNode } from "react";

interface EmptyStateProps {
  readonly title: string;
  readonly description?: string;
  readonly action?: ReactNode;
  readonly icon?: ReactNode;
  readonly className?: string;
}

/**
 * Standardized empty state component for consistent messaging across the application
 */
export function EmptyState({ 
  title, 
  description, 
  action, 
  icon,
  className = "" 
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 text-center ${className}`}>
      {icon && <div className="mb-4">{icon}</div>}
      <p className="text-sm font-medium text-muted-foreground mb-1">{title}</p>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

