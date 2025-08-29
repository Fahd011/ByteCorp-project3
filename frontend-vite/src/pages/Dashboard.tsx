/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
import { useState, useEffect, ChangeEvent, FormEvent } from "react";
import { toast } from "react-hot-toast";
import { credentialsAPI, providerAPI } from "../services/api";
import { Provider } from "../types";
// import { formatDate } from "../utils/helpers";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

const Dashboard: React.FC = () => {
  const [credentials, setCredentials] = useState<any[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [formData, setFormData] = useState({
    csvFile: null as File | null,
    selectedProviderId: "",
    loginUrl: "",
    billingUrl: "",
  });

  const navigate = useNavigate();

  useEffect(() => {
    fetchCredentials();
    fetchProviders();
  }, []);

  const fetchCredentials = async () => {
    try {
      const response = await credentialsAPI.getAll();
      setCredentials(response.data || []);
    } catch (error) {
      toast.error("Failed to load credentials");
    } finally {
      setLoading(false);
    }
  };

  const fetchProviders = async () => {
    try {
      const response = await providerAPI.getAll();
      setProviders(response.data || []);
    } catch (error) {
      toast.error("Failed to load providers");
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === "text/csv") {
      setFormData({ ...formData, csvFile: file });
    } else {
      toast.error("Please select a valid CSV file");
    }
  };

  const handleProviderChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const providerId = e.target.value;
    const selectedProvider = providers.find(p => p.id === providerId);
    
    setFormData({
      ...formData,
      selectedProviderId: providerId,
      loginUrl: selectedProvider?.login_url || "",
      billingUrl: selectedProvider?.billing_url || "",
    });
  };

  const handleCreateSession = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!formData.csvFile) {
      toast.error("Please select a CSV file");
      return;
    }

    if (!formData.selectedProviderId) {
      toast.error("Please select a provider");
      return;
    }

    if (!formData.loginUrl || !formData.billingUrl) {
      toast.error("Please fill in all required fields");
      return;
    }

    setUploading(true);

    try {
      const uploadData = new FormData();
      uploadData.append("csv_file", formData.csvFile);
      uploadData.append("login_url", formData.loginUrl);
      uploadData.append("billing_url", formData.billingUrl);

      const response = await credentialsAPI.upload(uploadData);
      
      // Handle the new response format with details
      const { message, details } = response.data;
      if (details) {
        const detailMessage = [];
        if (details.new_credentials > 0) {
          detailMessage.push(`${details.new_credentials} new credentials created`);
        }
        if (details.updated_credentials > 0) {
          detailMessage.push(`${details.updated_credentials} existing credentials updated`);
        }
        toast.success(`${message}: ${detailMessage.join(', ')}`);
      } else {
        toast.success(message);
      }

      // Reset form and close modal
      setFormData({
        csvFile: null,
        selectedProviderId: "",
        loginUrl: "",
        billingUrl: "",
      });
      setShowModal(false);

      // Refresh credentials list
      fetchCredentials();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  // const handleAgentControl = async (
  //   credId: string,
  //   action: "RUN" | "STOPPED"
  // ) => {
  //   try {
  //     await credentialsAPI.controlAgent(credId, { action });
  //     toast.success(`Agent ${action.toLowerCase()}`);
  //     fetchCredentials();
  //   } catch (error) {
  //     toast.error("Failed to control agent");
  //   }
  // };

  // const handleDelete = async (credId: string) => {
  //   try {
  //     await credentialsAPI.delete(credId);
  //     toast.success("Credential deleted");
  //     fetchCredentials();
  //   } catch (error) {
  //     toast.error("Failed to delete credential");
  //   }
  // };

  // const handleScheduleWeekly = async () => {
  //   try {
  //     await schedulingAPI.scheduleWeekly();
  //     toast.success('Weekly schedule created successfully');
  //     fetchCredentials();
  //   } catch (error) {
  //     toast.error('Failed to create weekly schedule');
  //   }
  // };

  const getStatusBadgeClass = (status: string | undefined) => {
    switch (status?.toLowerCase()) {
      case "idle":
        return "status-idle";
      case "running":
        return "status-running";
      case "completed":
        return "status-completed";
      case "error":
        return "status-error";
      case "pending":
        return "status-pending";
      default:
        return "status-idle";
    }
  };

  const getProviderIcon = (providerName: string) => {
    const name = providerName.toLowerCase();
    if (name.includes("duke") || name.includes("energy")) return "⚡";
    if (name.includes("gas") || name.includes("piedmont")) return "🔥";
    if (name.includes("water") || name.includes("charlotte")) return "💧";
    return "⚡";
  };

  const getProviderBadgeClass = (providerName: string) => {
    const name = providerName.toLowerCase();
    if (name.includes("duke") || name.includes("energy")) return "provider-energy";
    if (name.includes("gas") || name.includes("piedmont")) return "provider-gas";
    if (name.includes("water") || name.includes("charlotte")) return "provider-water";
    return "provider-energy";
  };

  const filteredCredentials = credentials.filter((cred) => {
    if (!searchTerm) return true;
    const searchLower = searchTerm.toLowerCase();
    return (
      cred.email.toLowerCase().includes(searchLower) ||
      (cred.utility_co_name && cred.utility_co_name.toLowerCase().includes(searchLower)) ||
      (cred.client_name && cred.client_name.toLowerCase().includes(searchLower))
    );
  });

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div>
      {/* Dashboard Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-title">Dashboard</h1>
        <p className="dashboard-subtitle">
          Manage your utility providers and billing
        </p>
      </div>

      {/* Stats Cards */}
      {/* <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-title">Total Credentials</div>
          <div className="stat-value">{credentials.length}</div>
          <span
            style={{ marginTop: "0.5rem", color: "#6b7280", fontSize: "24px" }}
          >
            👥
          </span>
        </div>

        <div className="stat-card">
          <div className="stat-title">Active Credentials</div>
          <div className="stat-value">
            {credentials.filter((c) => c.last_state === "running").length}
          </div>
          <span
            style={{ marginTop: "0.5rem", color: "#3b82f6", fontSize: "24px" }}
          >
            ⏰
          </span>
        </div>

        <div className="stat-card">
          <div className="stat-title">Completed Jobs</div>
          <div className="stat-value">
            {credentials.filter((c) => c.last_state === "completed").length}
          </div>
          <span
            style={{ marginTop: "0.5rem", color: "#10b981", fontSize: "24px" }}
          >
            ✅
          </span>
        </div>

        <div className="stat-card">
          <div className="stat-title">Failed Jobs</div>
          <div className="stat-value">
            {credentials.filter((c) => c.last_state === "error").length}
          </div>
          <span
            style={{ marginTop: "0.5rem", color: "#ef4444", fontSize: "24px" }}
          >
            ❌
          </span>
        </div>
      </div> */}

      {/* Search Section */}
      <div className="search-section">
        <div className="search-container">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search providers, clients, or account numbers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="results-count">
          Showing {filteredCredentials.length} of {credentials.length} providers
        </div>
      </div>

      {/* Create Session Button */}
      <div className="credentials-header">
        <div className="credentials-actions">
          <button
            onClick={() => setShowModal(true)}
            className="btn btn-primary"
            style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
          >
            ➕ Create Session
          </button>
        </div>
      </div>

      {/* Credentials Grid */}
      {filteredCredentials.length === 0 ? (
        <div className="empty-state">
          <span
            style={{ color: "#6b7280", marginBottom: "1rem", fontSize: "48px" }}
          >
            📧
          </span>
          <h3 style={{ color: "#374151", marginBottom: "0.5rem" }}>
            {searchTerm ? "No matching providers found" : "No credentials found"}
          </h3>
          <p style={{ color: "#6b7280", marginBottom: "1.5rem" }}>
            {searchTerm ? "Try adjusting your search terms" : "Get started by creating your first credential session."}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setShowModal(true)}
              className="btn btn-primary"
            >
              Create Session
            </button>
          )}
        </div>
      ) : (
        <div className="credentials-grid">
          {filteredCredentials.map((cred) => (
            <div key={cred.id} className="credential-card">
              <div className="credential-header">
                <h3 className="credential-email">{cred.email}</h3>
                <span
                  className={`status-badge ${getStatusBadgeClass(
                    cred.last_state || "idle"
                  )}`}
                >
                  ⏰ {cred.last_state ? cred.last_state : "Idle"}
                </span>
              </div>

              {/* {cred.last_run_time && (
                <div className="credential-detail">
                  <span className="credential-label">Last run:</span>
                  <span className="credential-value">
                    {formatDate(cred.last_run_time)}
                  </span>
                </div>
              )} */}

              <div className="credential-provider-section">
                <span className={`provider-badge ${getProviderBadgeClass(cred.utility_co_name || "")}`}>
                  {getProviderIcon(cred.utility_co_name || "")} {cred.utility_co_name || "Provider"}
                </span>
              </div>

              <div className="billing-cycle-info">
                <span className="cycle-text">
                  {cred.billing_cycle_day
                    ? (() => {
                        const today = new Date();
                        const currentDay = today.getDate();

                        // Actual run day is billing_cycle_day + 1
                        const runDay = cred.billing_cycle_day + 1;

                        let remainingDays: number;

                        if (currentDay === runDay) {
                          // Today is the run day
                          remainingDays = 0;
                        } else if (currentDay < runDay) {
                          // Run day later this month
                          remainingDays = runDay - currentDay;
                        } else {
                          // Run day passed → schedule for next month
                          const nextMonth = new Date(
                            today.getFullYear(),
                            today.getMonth() + 1,
                            0
                          ); // last day of current month
                          const daysInMonth = nextMonth.getDate();
                          remainingDays = daysInMonth - currentDay + runDay;
                        }

                        return remainingDays === 0
                          ? "Your bill cycle runs today."
                          : `Your bill cycle runs in ${remainingDays} day${
                              remainingDays > 1 ? "s" : ""
                            }.`;
                      })()
                    : "Bill cycle information not available."}
                </span>
              </div>

              <div className="credential-links">
                <a
                  href={cred.login_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="credential-link"
                >
                  🔗 Login Portal
                </a>
                <a
                  href={cred.billing_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="credential-link"
                >
                  🔗 Billing History
                </a>
              </div>

              <div className="credential-actions">
                <button
                  onClick={() => navigate(`/billing-results/${cred.id}`)}
                  className="btn btn-primary"
                >
                  View Bills
                </button>
                {/* {cred.last_state !== "running" && (
                  <button
                    onClick={() => handleAgentControl(cred.id, "RUN")}
                    className="btn btn-success"
                  >
                    ▶️ Start
                  </button>
                )}
                {cred.last_state === "running" && (
                  <button
                    onClick={() => handleAgentControl(cred.id, "STOPPED")}
                    className="btn btn-danger"
                  >
                    ⏹️ Stop
                  </button>
                )}
                <button
                  onClick={() => handleDelete(cred.id)}
                  className="btn btn-danger"
                >
                  🗑️ Delete
                </button> */}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Session Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Create New Session</h2>
              <button
                onClick={() => setShowModal(false)}
                className="modal-close"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateSession}>
              <div className="form-group">
                <label htmlFor="csvFile" className="form-label">
                  CSV File
                </label>
                <input
                  type="file"
                  id="csvFile"
                  accept=".csv"
                  onChange={handleFileChange}
                  className="form-input"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="providerSelect" className="form-label">
                  Provider
                </label>
                <select
                  id="providerSelect"
                  value={formData.selectedProviderId}
                  onChange={handleProviderChange}
                  className="form-input"
                  required
                >
                  <option value="">Select a provider...</option>
                  {providers.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.name}
                    </option>
                  ))}
                </select>
              </div>



              <div
                style={{
                  display: "flex",
                  gap: "1rem",
                  justifyContent: "flex-end",
                }}
              >
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={uploading}
                >
                  {uploading ? "Creating..." : "Create Session"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
