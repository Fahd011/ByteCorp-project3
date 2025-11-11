import { useState, useEffect, ChangeEvent, FormEvent } from "react";
import { toast } from "react-hot-toast";
import { credentialsAPI, providerAPI } from "../services/api";
import { Provider } from "../types";
import { useNavigate } from "react-router-dom";

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

  const handleDelete = async (credId: string) => {
    // Show confirmation dialog
    if (!window.confirm("Are you sure you want to delete this credential? This action cannot be undone and will also delete all associated billing results.")) {
      return;
    }
    
    try {
      await credentialsAPI.delete(credId);
      toast.success("Credential deleted successfully");
      fetchCredentials();
    } catch (error) {
      toast.error("Failed to delete credential");
    }
  };

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
    return <div className="flex justify-center items-center h-[200px] text-slate-500">Loading...</div>;
  }

  return (
    <div>
      {/* Dashboard Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-slate-800 m-0 mb-2">Dashboard</h1>
        <p className="text-slate-500 text-base m-0">
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
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-base">🔍</span>
          <input
            type="text"
            placeholder="Search providers, clients, or account numbers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full py-3 pr-4 pl-10 border border-gray-300 rounded-lg text-sm bg-white transition-[border-color] duration-200 box-border focus:outline-none focus:border-blue-500 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.1)]"
          />
        </div>
        <div className="text-slate-500 text-sm whitespace-nowrap">
          Showing {filteredCredentials.length} of {credentials.length} providers
        </div>
      </div>

      {/* Create Session Button */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex gap-4">
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-6 py-3 border-0 rounded-lg font-medium text-sm cursor-pointer transition-all duration-200 no-underline bg-blue-500 text-white hover:bg-blue-600"
          >
            ➕ Create Session
          </button>
        </div>
      </div>

      {/* Credentials Grid */}
      {filteredCredentials.length === 0 ? (
        <div className="text-center p-12 bg-white rounded-xl border border-slate-200">
          <span className="text-gray-500 mb-4 text-5xl block">
            📧
          </span>
          <h3 className="text-gray-700 mb-2">
            {searchTerm ? "No matching providers found" : "No credentials found"}
          </h3>
          <p className="text-gray-500 mb-6">
            {searchTerm ? "Try adjusting your search terms" : "Get started by creating your first credential session."}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setShowModal(true)}
              className="inline-flex items-center gap-2 px-6 py-3 border-0 rounded-lg font-medium text-sm cursor-pointer transition-all duration-200 no-underline bg-blue-500 text-white hover:bg-blue-600"
            >
              Create Session
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(350px,1fr))] gap-6 mt-8">
          {filteredCredentials.map((cred) => (
            <div key={cred.id} className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 transition-all duration-200 hover:shadow-md">
              <div className="flex justify-between items-center gap-3 mb-4">
                <h3 className="font-semibold text-slate-800 m-0 text-base leading-normal flex-1 min-w-0 truncate" title={cred.email}>{cred.email}</h3>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium capitalize flex items-center gap-1 flex-shrink-0 ${
                    getStatusBadgeClass(cred.last_state || "idle") === "status-idle" 
                      ? "bg-slate-100 text-slate-500"
                      : getStatusBadgeClass(cred.last_state || "idle") === "status-running"
                      ? "bg-emerald-100 text-emerald-800"
                      : getStatusBadgeClass(cred.last_state || "idle") === "status-completed"
                      ? "bg-emerald-100 text-emerald-800"
                      : getStatusBadgeClass(cred.last_state || "idle") === "status-error"
                      ? "bg-red-100 text-red-600"
                      : "bg-amber-100 text-amber-800"
                  }`}
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
                <span className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${
                  getProviderBadgeClass(cred.utility_co_name || "") === "provider-energy"
                    ? "bg-amber-100 text-amber-800"
                    : getProviderBadgeClass(cred.utility_co_name || "") === "provider-gas"
                    ? "bg-orange-200 text-orange-900"
                    : "bg-blue-100 text-blue-800"
                }`}>
                  {getProviderIcon(cred.utility_co_name || "")} {cred.utility_co_name || "Provider"}
                </span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 mb-4">
                <span className="text-slate-500 text-sm leading-normal m-0">
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
                  className="flex items-center gap-2 text-blue-500 no-underline text-sm font-medium transition-colors duration-200 hover:text-blue-600 hover:underline"
                >
                  🔗 Login Portal
                </a>
                <a
                  href={cred.billing_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-blue-500 no-underline text-sm font-medium transition-colors duration-200 hover:text-blue-600 hover:underline"
                >
                  🔗 Billing History
                </a>
              </div>

              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => navigate(`/billing-results/${cred.id}`)}
                  className="px-6 py-3 text-sm font-semibold flex-1 min-w-0 justify-center bg-blue-500 border-0 rounded-lg text-white cursor-pointer transition-all duration-200 hover:bg-blue-600 hover:-translate-y-0.5"
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
                )} */}
                <button
                  onClick={() => handleDelete(cred.id)}
                  className="flex items-center justify-center gap-1.5 py-2 px-3.5 text-[0.8125rem] font-semibold bg-gradient-to-br from-red-500 to-red-600 text-white border-0 rounded-lg cursor-pointer transition-all duration-200 shadow-[0_2px_4px_rgba(239,68,68,0.2)] w-auto flex-[0_0_auto] hover:bg-gradient-to-br hover:from-red-600 hover:to-red-700 hover:-translate-y-0.5 hover:shadow-[0_4px_8px_rgba(239,68,68,0.3)] active:translate-y-0 active:shadow-[0_1px_2px_rgba(239,68,68,0.2)]"
                  title="Delete credential"
                >
                  <span className="text-sm flex items-center">🗑️</span>
                  <span className="font-semibold tracking-wide">Delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Session Modal */}
      {showModal && (
        <div className="fixed top-0 left-0 right-0 bottom-0 bg-black/50 flex justify-center items-center z-[1000]" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-xl p-8 w-[90%] max-w-[500px] shadow-[0_20px_25px_-5px_rgba(0,0,0,0.1),0_10px_10px_-5px_rgba(0,0,0,0.04)]" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-slate-800 m-0">Create New Session</h2>
              <button
                onClick={() => setShowModal(false)}
                className="bg-transparent border-0 text-2xl cursor-pointer text-slate-500 p-0 w-8 h-8 flex items-center justify-center rounded-md hover:bg-slate-100 hover:text-slate-800"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateSession}>
              <div className="mb-6">
                <label htmlFor="csvFile" className="block font-medium text-gray-700 mb-2 text-sm">
                  CSV File
                </label>
                <input
                  type="file"
                  id="csvFile"
                  accept=".csv"
                  onChange={handleFileChange}
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm transition-[border-color] duration-200 focus:outline-none focus:border-blue-500 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.1)] file:py-2 file:px-4 file:border file:border-gray-300 file:rounded-md file:bg-gray-50 file:text-gray-700 file:text-sm file:cursor-pointer file:mr-4 file:hover:bg-gray-100"
                  required
                />
              </div>

              <div className="mb-6">
                <label htmlFor="providerSelect" className="block font-medium text-gray-700 mb-2 text-sm">
                  Provider
                </label>
                <select
                  id="providerSelect"
                  value={formData.selectedProviderId}
                  onChange={handleProviderChange}
                  className="w-full py-3.5 px-4 border-2 border-gray-200 rounded-xl text-sm font-medium bg-white appearance-none cursor-pointer transition-all duration-300 shadow-sm text-gray-700 hover:border-blue-500 hover:bg-blue-50/30 hover:shadow-[0_4px_12px_rgba(59,130,246,0.15),0_2px_4px_rgba(0,0,0,0.1)] hover:-translate-y-0.5 focus:outline-none focus:border-blue-500 focus:shadow-[0_0_0_4px_rgba(59,130,246,0.15),0_4px_12px_rgba(59,130,246,0.1)] focus:bg-blue-50/30 focus:-translate-y-0.5 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:opacity-70 disabled:border-gray-200 disabled:shadow-none disabled:translate-y-0 [background-image:url('data:image/svg+xml,%3csvg xmlns=%27http://www.w3.org/2000/svg%27 fill=%27none%27 viewBox=%270 0 24 24%27 stroke=%27%236b7280%27%3e%3cpath stroke-linecap=%27round%27 stroke-linejoin=%27round%27 stroke-width=%272%27 d=%27M19 9l-7 7-7-7%27/%3e%3c/svg%3e')] [background-position:right_1rem_center] [background-repeat:no-repeat] [background-size:1.25em_1.25em]"
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



              <div className="flex gap-4 justify-end">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="inline-flex items-center gap-2 px-6 py-3 border-0 rounded-lg font-medium text-sm cursor-pointer transition-all duration-200 no-underline bg-slate-500 text-white hover:bg-slate-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 px-6 py-3 border-0 rounded-lg font-medium text-sm cursor-pointer transition-all duration-200 no-underline bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-60 disabled:cursor-not-allowed"
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
