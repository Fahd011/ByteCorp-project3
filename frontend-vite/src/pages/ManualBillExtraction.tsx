/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, ChangeEvent, FormEvent } from "react";
import { toast } from "react-hot-toast";
import { manualBillsAPI, providerAPI, credentialsAPI } from "../services/api";
import { Provider, ManualBill } from "../types";
import "./ManualBillExtraction.css";

const ManualBillExtraction: React.FC = () => {
  const [manualBills, setManualBills] = useState<ManualBill[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [formData, setFormData] = useState({
    pdfFile: null as File | null,
    selectedProviderId: "",
  });

  useEffect(() => {
    fetchManualBills();
    fetchProviders();
  }, []);

  const fetchManualBills = async () => {
    try {
      const response = await manualBillsAPI.getAll();
      setManualBills(response.data || []);
    } catch (error) {
      toast.error("Failed to load manual bills");
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
    if (file && file.type === "application/pdf") {
      setFormData({ ...formData, pdfFile: file });
    } else {
      toast.error("Please select a valid PDF file");
    }
  };

  const handleProviderChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const providerId = e.target.value;
    setFormData({
      ...formData,
      selectedProviderId: providerId,
    });
  };

  const handleUploadBill = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!formData.pdfFile) {
      toast.error("Please select a PDF file");
      return;
    }

    if (!formData.selectedProviderId) {
      toast.error("Please select a provider");
      return;
    }

    setUploading(true);

    try {
      const uploadData = new FormData();
      uploadData.append("pdf_file", formData.pdfFile);
      uploadData.append("provider_id", formData.selectedProviderId);

      const response = await manualBillsAPI.upload(uploadData);

      toast.success(response.data.message || "Bill uploaded successfully");

      // Reset form and close modal
      setFormData({
        pdfFile: null,
        selectedProviderId: "",
      });
      setShowModal(false);

      // Refresh manual bills list
      fetchManualBills();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status?.toLowerCase()) {
      case "processing":
        return "status-running";
      case "completed":
        return "status-completed";
      case "error":
        return "status-error";
      case "manual_upload":
        return "status-idle";
      default:
        return "status-idle";
    }
  };

  const getProviderIcon = (providerName: string) => {
    const name = providerName?.toLowerCase() || "";
    if (name.includes("duke") || name.includes("energy")) return "⚡";
    if (name.includes("gas") || name.includes("piedmont")) return "🔥";
    if (name.includes("water") || name.includes("charlotte")) return "💧";
    return "📄";
  };

  const getProviderBadgeClass = (providerName: string) => {
    const name = providerName?.toLowerCase() || "";
    if (name.includes("duke") || name.includes("energy"))
      return "provider-energy";
    if (name.includes("gas") || name.includes("piedmont"))
      return "provider-gas";
    if (name.includes("water") || name.includes("charlotte"))
      return "provider-water";
    return "provider-energy";
  };

  const handleDownload = async (blobName: string, fileType: string) => {
    try {
      const response = await credentialsAPI.downloadPDF(blobName);
      const blob = new Blob([response.data], {
        type:
          fileType === "pdf"
            ? "application/pdf"
            : fileType === "json"
            ? "application/json"
            : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = blobName.split("/").pop() || `download.${fileType}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success(`${fileType.toUpperCase()} downloaded successfully`);
    } catch (error) {
      toast.error(`Failed to download ${fileType.toUpperCase()}`);
    }
  };

  const filteredBills = manualBills.filter((bill) => {
    if (!searchTerm) return true;
    const searchLower = searchTerm.toLowerCase();
    return (
      (bill.original_filename &&
        bill.original_filename.toLowerCase().includes(searchLower)) ||
      (bill.provider_name &&
        bill.provider_name.toLowerCase().includes(searchLower))
    );
  });

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div>
      {/* Page Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-title">Manual Bill Extraction</h1>
        <p className="dashboard-subtitle">
          Upload bills manually for automatic data extraction
        </p>
      </div>

      {/* Search Section */}
      <div className="search-section">
        <div className="search-container">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search by filename or provider..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="results-count">
          Showing {filteredBills.length} of {manualBills.length} bills
        </div>
      </div>

      {/* Upload Bill Button */}
      <div className="credentials-header">
        <div className="credentials-actions">
          <button
            onClick={() => setShowModal(true)}
            className="btn btn-primary"
            style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
          >
            ➕ Upload Bill
          </button>
        </div>
      </div>

      {/* Bills Grid */}
      {filteredBills.length === 0 ? (
        <div className="empty-state">
          <span
            style={{ color: "#6b7280", marginBottom: "1rem", fontSize: "48px" }}
          >
            📄
          </span>
          <h3 style={{ color: "#374151", marginBottom: "0.5rem" }}>
            {searchTerm ? "No matching bills found" : "No bills uploaded yet"}
          </h3>
          <p style={{ color: "#6b7280", marginBottom: "1.5rem" }}>
            {searchTerm
              ? "Try adjusting your search terms"
              : "Get started by uploading your first bill for extraction."}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setShowModal(true)}
              className="btn btn-primary"
            >
              Upload Bill
            </button>
          )}
        </div>
      ) : (
        <div className="credentials-grid">
          {filteredBills.map((bill) => (
            <div key={bill.id} className="credential-card">
              <div className="credential-header">
                <h3 className="credential-email">
                  {bill.original_filename || "Unnamed Bill"}
                </h3>
                <span
                  className={`status-badge ${getStatusBadgeClass(bill.status)}`}
                >
                  ⏰ {bill.status}
                </span>
              </div>

              <div className="credential-provider-section">
                <span
                  className={`provider-badge ${getProviderBadgeClass(
                    bill.provider_name || ""
                  )}`}
                >
                  {getProviderIcon(bill.provider_name || "")}{" "}
                  {bill.provider_name || "Unknown Provider"}
                </span>
              </div>

              <div className="billing-cycle-info">
                <span className="cycle-text">
                  Uploaded: {bill.month} {bill.year}
                </span>
              </div>

              <div className="credential-actions">
                <button
                  onClick={() => handleDownload(bill.azure_blob_url, "pdf")}
                  className="btn btn-primary"
                  title="Download PDF"
                >
                  📄 PDF
                </button>
                {bill.excel_blob_url && (
                  <button
                    onClick={() => handleDownload(bill.excel_blob_url!, "xlsx")}
                    className="btn btn-success"
                    title="Download Excel"
                  >
                    📊 Excel
                  </button>
                )}
                {bill.json_blob_url && (
                  <button
                    onClick={() => handleDownload(bill.json_blob_url!, "json")}
                    className="btn btn-secondary"
                    title="Download JSON"
                  >
                    📋 JSON
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Bill Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Upload Bill</h2>
              <button
                onClick={() => setShowModal(false)}
                className="modal-close"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleUploadBill}>
              <div className="form-group">
                <label htmlFor="pdfFile" className="form-label">
                  PDF File
                </label>
                <input
                  type="file"
                  id="pdfFile"
                  accept=".pdf"
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
                  {uploading ? "Uploading..." : "Upload Bill"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ManualBillExtraction;
