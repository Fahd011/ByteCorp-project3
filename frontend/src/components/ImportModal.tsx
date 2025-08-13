import React, { useState } from "react";
import { CreateJobData } from "../types";
import ScheduleConfig from "./ScheduleConfig";

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateJobData) => void;
  isLoading: boolean;
}

const ImportModal: React.FC<ImportModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
}) => {
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [loginUrl, setLoginUrl] = useState("");
  const [billingUrl, setBillingUrl] = useState("");
  const [error, setError] = useState("");
  const [scheduleConfig, setScheduleConfig] = useState<{
    is_scheduled: boolean;
    schedule_type: "weekly" | "daily" | "monthly" | "custom";
    schedule_config: {
      day_of_week: number;
      hour: number;
      minute: number;
      cron_expression: string;
    };
  }>({
    is_scheduled: false,
    schedule_type: "weekly",
    schedule_config: {
      day_of_week: 1, // Monday
      hour: 9,
      minute: 0,
      cron_expression: "",
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!csvFile || !loginUrl || !billingUrl) {
      setError("Please fill in all fields");
      return;
    }

    const jobData: CreateJobData = {
      csv: csvFile,
      login_url: loginUrl,
      billing_url: billingUrl,
      ...scheduleConfig, // Include scheduling configuration
    };

    // Debug logging
    console.log("🚀 Creating job with data:", jobData);
    console.log("📅 Schedule config:", scheduleConfig);

    onSubmit(jobData);
    onClose();
    resetForm();
  };

  const resetForm = () => {
    setCsvFile(null);
    setLoginUrl("");
    setBillingUrl("");
    setError("");
    setScheduleConfig({
      is_scheduled: false,
      schedule_type: "weekly",
      schedule_config: {
        day_of_week: 1,
        hour: 9,
        minute: 0,
        cron_expression: "",
      },
    });
  };

  if (!isOpen) return null;

  return (
    <div style={modalStyles.overlay} onClick={onClose}>
      <div style={modalStyles.modal} onClick={(e) => e.stopPropagation()}>
        <h2>Create New Job</h2>

        <form onSubmit={handleSubmit}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>CSV File:</label>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
              style={styles.fileInput}
              required
            />
          </div>

          <div style={styles.inputGroup}>
            <label style={styles.label}>Login URL:</label>
            <input
              type="url"
              value={loginUrl}
              onChange={(e) => setLoginUrl(e.target.value)}
              style={styles.input}
              placeholder="https://example.com/login"
              required
            />
          </div>

          <div style={styles.inputGroup}>
            <label style={styles.label}>Billing URL:</label>
            <input
              type="url"
              value={billingUrl}
              onChange={(e) => setBillingUrl(e.target.value)}
              style={styles.input}
              placeholder="https://example.com/billing"
              required
            />
          </div>

          {/* Add ScheduleConfig component */}
          <ScheduleConfig
            isScheduled={scheduleConfig.is_scheduled}
            scheduleType={scheduleConfig.schedule_type}
            scheduleConfig={scheduleConfig.schedule_config}
            onScheduleChange={setScheduleConfig}
          />

          {error && <p style={styles.error}>{error}</p>}

          <div style={styles.actions}>
            <button type="button" onClick={onClose} style={styles.cancelButton}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !csvFile || !loginUrl || !billingUrl}
              style={styles.submitButton}
            >
              {isLoading ? "Creating..." : "Create Job"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const styles = {
  overlay: {
    position: "fixed" as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1000,
  },
  modal: {
    backgroundColor: "white",
    borderRadius: "8px",
    padding: "2rem",
    width: "90%",
    maxWidth: "500px",
    maxHeight: "90vh",
    overflow: "auto",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "1.5rem",
  },
  title: {
    margin: 0,
    color: "#333",
  },
  closeButton: {
    backgroundColor: "transparent",
    border: "none",
    fontSize: "1.5rem",
    cursor: "pointer",
    color: "#666",
  },
  form: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "1rem",
  },
  inputGroup: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "0.5rem",
  },
  label: {
    fontWeight: "bold",
    color: "#333",
  },
  input: {
    padding: "0.75rem",
    border: "1px solid #ddd",
    borderRadius: "4px",
    fontSize: "1rem",
  },
  fileInput: {
    padding: "0.5rem",
    border: "1px solid #ddd",
    borderRadius: "4px",
    fontSize: "1rem",
  },
  actions: {
    display: "flex",
    gap: "1rem",
    marginTop: "1rem",
  },
  cancelButton: {
    padding: "0.75rem 1.5rem",
    backgroundColor: "#6c757d",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "1rem",
  },
  submitButton: {
    padding: "0.75rem 1.5rem",
    backgroundColor: "#007bff",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "1rem",
    flex: 1,
  },
  error: {
    color: "red",
    marginTop: "10px",
    fontSize: "0.9rem",
  },
};

const modalStyles = {
  overlay: {
    position: "fixed" as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1000,
  },
  modal: {
    backgroundColor: "white",
    borderRadius: "8px",
    padding: "2rem",
    width: "90%",
    maxWidth: "500px",
    maxHeight: "90vh",
    overflow: "auto",
  },
};

export default ImportModal;
