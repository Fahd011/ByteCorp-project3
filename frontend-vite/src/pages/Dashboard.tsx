/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
import { useState, useEffect, ChangeEvent, FormEvent } from "react";
import { toast } from "react-hot-toast";
import { credentialsAPI, providerAPI } from "../services/api";
import { Provider } from "../types";
// import { formatDate } from "../utils/helpers";
import { useNavigate } from "react-router-dom";


const Dashboard: React.FC = () => {
  const [credentials, setCredentials] = useState<any[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [credentialProviders, setCredentialProviders] = useState<{[key: string]: string}>({});
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
      uploadData.append("provider_id", formData.selectedProviderId);

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

      // Get the selected provider name
      const selectedProvider = providers.find(p => p.id === formData.selectedProviderId);
      const providerName = selectedProvider?.name || "Unknown Provider";

      // Reset form and close modal
      setFormData({
        csvFile: null,
        selectedProviderId: "",
        loginUrl: "",
        billingUrl: "",
      });
      setShowModal(false);

      // Refresh credentials list and store provider mapping
      await fetchCredentials();
      
      // Store provider name for newly created credentials
      const newCredentials = await credentialsAPI.getAll();
      const latestCredentials = newCredentials.data || [];
      const updatedProviders = { ...credentialProviders };
      
      // Map the latest credentials to the selected provider
      latestCredentials.forEach((cred: any) => {
        if (!credentialProviders[cred.id]) {
          updatedProviders[cred.id] = providerName;
        }
      });
      
      setCredentialProviders(updatedProviders);
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

  const getProviderName = (utilityCoName: string) => {
    // Map utility company names to provider names
    const name = utilityCoName.toLowerCase();
    if (name.includes("duke")) return "Duke Energy";
    if (name.includes("piedmont")) return "Piedmont Gas";
    if (name.includes("charlotte")) return "Charlotte Water";
    if (name.includes("energy")) return "Energy Provider";
    if (name.includes("gas")) return "Gas Provider";
    if (name.includes("water")) return "Water Provider";
    return utilityCoName || "Provider";
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
    return <div className="loading flex justify-center items-center h-48 text-slate-500">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Dashboard Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-semibold text-slate-800 m-0 mb-2">Dashboard</h1>
        <p className=" text-slate-500 text-base m-0">
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
      <div className="flex justify-between items-center mb-8 gap-4">
        <div className="relative flex-1 max-w-[800px]">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-base">🔍</span>
          <input
            type="text"
            placeholder="Search providers, clients, or account numbers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-lg text-sm bg-white transition focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10"
          />
        </div>
        <div className=" text-slate-500 text-sm whitespace-nowrap">
          Showing {filteredCredentials.length} of {credentials.length} providers
        </div>
      </div>

      {/* Create Session Button */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex gap-4">
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 transition"
            style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
          >
            ➕ Create Session
          </button>
        </div>
      </div>

      {/* Credentials Grid */}
      {filteredCredentials.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
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
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 transition"
            >
              Create Session
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
          {filteredCredentials.map((cred) => (
            <div key={cred.id} className=" bg-white rounded-xl p-6 shadow-sm border border-slate-200 transition hover:shadow-lg">
              <div className="flex justify-between items-start mb-4">
                <h3 className="font-semibold text-slate-800 m-0 text-base">{cred.email}</h3>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium capitalize flex items-center gap-1 ${getStatusBadgeClass(
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

              <div className="flex justify-between items-center mb-4">
                <span className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${getProviderBadgeClass(credentialProviders[cred.id] || cred.provider_name || cred.utility_co_name || "")}`}>
                  {getProviderIcon(credentialProviders[cred.id] || cred.provider_name || cred.utility_co_name || "")} {credentialProviders[cred.id] || cred.provider_name || getProviderName(cred.utility_co_name || "")}
                </span>
              </div>

              <div className=" bg-slate-50 border border-slate-200 rounded-lg p-3 mb-4">
                <span className=" text-slate-500 text-sm">
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

              <div className="mb-4 flex flex-row gap-4">
                <a
                  href={cred.login_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-blue-500 hover:underline text-sm font-medium"
                >
                  🔗 Login Portal
                </a>
                <a
                  href={cred.billing_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-blue-500 hover:underline text-sm font-medium"
                >
                  🔗 Billing History
                </a>
              </div>

              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => navigate(`/billing-results/${cred.id}`)}
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold bg-blue-500 text-white hover:bg-blue-600 transition w-full"
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
        <div className="fixed inset-0 bg-black/50 flex justify-center items-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-xl p-0 max-w-lg w-11/12 max-h-[90vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center px-6 py-5 border-b border-slate-200">
              <h2 className="m-0 text-xl font-semibold text-slate-800">Create New Session</h2>
              <button
                onClick={() => setShowModal(false)}
                className="bg-transparent border-none text-2xl cursor-pointer text-slate-500 p-1 rounded hover:bg-slate-100 hover:text-slate-600 transition"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateSession} className="p-6">
              <div className="mb-5">
                <label htmlFor="csvFile" className="block mb-2 font-medium text-slate-700 text-sm">
                  CSV File
                </label>
                <input
                  type="file"
                  id="csvFile"
                  accept=".csv"
                  onChange={handleFileChange}
                  className="w-full px-4 py-3 border-2 border-slate-200 rounded-xl text-sm font-medium bg-gradient-to-br from-white to-slate-50 transition-all duration-300 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/15 hover:border-blue-500 hover:-translate-y-px focus:-translate-y-px shadow-sm hover:shadow-md file:px-4 file:py-2 file:border file:border-slate-300 file:rounded-md file:bg-slate-50 file:text-slate-700 file:text-sm file:font-medium file:cursor-pointer file:hover:bg-slate-100 file:transition-colors"
                  required
                />
              </div>

              <div className="mb-5">
                <label htmlFor="providerSelect" className="block mb-2 font-medium text-slate-700 text-sm">
                  Provider
                </label>
                <select
                  id="providerSelect"
                  value={formData.selectedProviderId}
                  onChange={handleProviderChange}
                  className="w-full px-4 py-3 pr-12 border-2 border-slate-200 rounded-xl text-sm font-medium bg-white appearance-none cursor-pointer transition-all duration-300 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/15 hover:border-blue-500 hover:-translate-y-px focus:-translate-y-px shadow-sm hover:shadow-md"
                  style={{ 
                    backgroundImage: "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%236b7280'%3e%3cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3e%3c/svg%3e\")",
                    backgroundPosition: "right 1rem center",
                    backgroundRepeat: "no-repeat",
                    backgroundSize: "1.25em 1.25em"
                  }}
                  required
                >
                  <option value="" className="py-2 px-3 bg-white text-slate-700 font-medium">Select a provider...</option>
                  {providers.map((provider) => (
                    <option key={provider.id} value={provider.id} className="py-2 px-3 bg-white text-slate-700 font-medium hover:bg-blue-50 hover:text-blue-700">
                      {provider.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-5 py-2.5 border-none rounded-md text-sm font-medium cursor-pointer bg-slate-100 text-slate-700 hover:bg-slate-200 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 border-none rounded-md text-sm font-medium cursor-pointer bg-blue-500 text-white hover:bg-blue-600 disabled:bg-slate-400 disabled:cursor-not-allowed transition"
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
