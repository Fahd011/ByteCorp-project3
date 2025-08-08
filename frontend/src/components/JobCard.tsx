import React from "react";
import { Job } from "../types";

interface JobCardProps {
  job: Job;
  onRun: (jobId: string) => void;
  onStop: (jobId: string) => void;
  onDelete: (jobId: string) => void;
  onViewResults: (jobId: string) => void;
  onViewCredentials: (jobId: string) => void;
  isLoading: boolean;
  isInCooldown?: boolean;
  cooldownRemaining?: number;
}

const JobCard: React.FC<JobCardProps> = ({
  job,
  onRun,
  onStop,
  onDelete,
  onViewResults,
  onViewCredentials,
  isLoading,
  isInCooldown = false,
  cooldownRemaining = 0,
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "#007bff";
      case "completed":
        return "#28a745";
      case "stopped":
        return "#ffc107";
      case "error":
        return "#dc3545";
      default:
        return "#6c757d";
    }
  };

  const getStatusText = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return "Invalid Date";
      }
      return date.toLocaleDateString() + " " + date.toLocaleTimeString();
    } catch (error) {
      console.error("Error formatting date:", dateString, error);
      return "Invalid Date";
    }
  };

  // Determine which buttons to show based on job status
  const canStop = job.status === "running";
  const canDelete =
    job.status === "idle" || job.status === "stopped" || job.status === "error";

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <div style={styles.statusContainer}>
          <span
            style={{
              ...styles.statusBadge,
              backgroundColor: getStatusColor(job.status),
            }}
          >
            {getStatusText(job.status)}
          </span>
        </div>
        <div style={styles.date}>{formatDate(job.created_at)}</div>
      </div>

      <div style={styles.content}>
        <div style={styles.urlGroup}>
          <strong>Login URL:</strong>
          <span style={styles.url}>{job.login_url}</span>
        </div>
        <div style={styles.urlGroup}>
          <strong>Billing URL:</strong>
          <span style={styles.url}>{job.billing_url}</span>
        </div>
        <div style={styles.results}>
          <strong>Results:</strong> {job.results_count} items
        </div>
      </div>

      <div style={styles.actions}>
        {(job.status === "idle" ||
          job.status === "stopped" ||
          job.status === "error") && (
          <button
            onClick={() => onRun(job.id)}
            disabled={isLoading || isInCooldown}
            style={{
              ...styles.runButton,
              ...(isInCooldown && styles.disabledButton),
            }}
            title={
              isInCooldown
                ? `Job is in cooldown. Please wait ${cooldownRemaining} more seconds.`
                : "Run this job"
            }
          >
            {isInCooldown ? `Run (${cooldownRemaining}s)` : "Run"}
          </button>
        )}

        {canStop && (
          <button
            onClick={() => onStop(job.id)}
            disabled={isLoading}
            style={styles.stopButton}
          >
            Stop
          </button>
        )}

        {canDelete && (
          <button
            onClick={() => onDelete(job.id)}
            disabled={isLoading}
            style={styles.deleteButton}
          >
            Delete
          </button>
        )}

        {job.status === "completed" && (
          <button
            onClick={() => onViewResults(job.id)}
            disabled={isLoading}
            style={styles.viewResultsButton}
          >
            View Results
          </button>
        )}

        <button
          onClick={() => onViewCredentials(job.id)}
          disabled={isLoading}
          style={styles.viewCredentialsButton}
        >
          View Credentials
        </button>
      </div>
    </div>
  );
};

const styles = {
  card: {
    backgroundColor: "white",
    borderRadius: "8px",
    padding: "1.5rem",
    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
    border: "1px solid #e0e0e0",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "1rem",
  },
  statusContainer: {
    display: "flex",
    alignItems: "center",
  },
  statusBadge: {
    padding: "0.25rem 0.75rem",
    borderRadius: "20px",
    color: "white",
    fontSize: "0.875rem",
    fontWeight: "bold",
  },
  date: {
    color: "#666",
    fontSize: "0.875rem",
  },
  content: {
    marginBottom: "1rem",
  },
  urlGroup: {
    marginBottom: "0.5rem",
  },
  url: {
    display: "block",
    color: "#007bff",
    fontSize: "0.875rem",
    wordBreak: "break-all" as const,
    marginTop: "0.25rem",
  },
  results: {
    marginTop: "0.5rem",
    color: "#666",
  },
  actions: {
    display: "flex",
    gap: "0.5rem",
    flexWrap: "wrap" as const,
  },
  runButton: {
    padding: "0.5rem 1rem",
    backgroundColor: "#28a745",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.875rem",
  },
  stopButton: {
    padding: "0.5rem 1rem",
    backgroundColor: "#ffc107",
    color: "#212529",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.875rem",
  },
  deleteButton: {
    padding: "0.5rem 1rem",
    backgroundColor: "#dc3545",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.875rem",
  },
  viewResultsButton: {
    padding: "0.5rem 1rem",
    backgroundColor: "#17a2b8",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.875rem",
  },
  viewCredentialsButton: {
    padding: "0.5rem 1rem",
    backgroundColor: "#6f42c1",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.875rem",
  },
  disabledButton: {
    backgroundColor: "#6c757d",
    color: "#fff",
    cursor: "not-allowed",
    opacity: 0.6,
  },
};

export default JobCard;
