/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { credentialsAPI } from "../services/api";
import "./BillingResults.css"; // custom CSS file
import toast from "react-hot-toast";
import UploadModal from "../components/UploadModal";

const BillingResults: React.FC = () => {
  const { cred_id: credId } = useParams();
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  useEffect(() => {
    fetchResults();
  }, [credId]);

  const handleDownloadPDF = async (blobName: string) => {
    try {
      const response = await credentialsAPI.downloadPDF(blobName);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `bill_${blobName}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("PDF downloaded successfully");
    } catch (error) {
      toast.error("Failed to download PDF");
    }
  };

  const handleUploadManualPDF = async (file: File, year: string, month: string) => {
    if (!credId) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("pdf_file", file);
      formData.append("year", year);
      formData.append("month", month);

      await credentialsAPI.uploadManualPDF(credId, formData);
      toast.success("PDF uploaded successfully");
      
      // Refresh the billing results
      fetchResults();
      setShowUploadModal(false);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to upload PDF");
    } finally {
      setUploading(false);
    }
  };

  const fetchResults = async () => {
    try {
      if (credId) {
        const response = await credentialsAPI.getBillingResults(credId);
        setResults(response.data || []);
      }
    } catch (err) {
      console.error("❌ Failed to fetch billing results", err);
      toast.error("Failed to fetch billing results");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="billing-container">
      <h2 className="billing-title">Billing Results</h2>

      {/* Manual PDF Upload Section */}
      <div className="manual-pdf-section">
        <h3 className="manual-pdf-title">Upload Manual PDF Bill</h3>
        <div className="manual-pdf-actions">
          <button
            onClick={() => setShowUploadModal(true)}
            disabled={uploading}
            className="upload-btn"
          >
            {uploading ? "Uploading..." : "📁 Upload PDF Bill"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-spinner-container">
          <div className="loading-spinner"></div>
          <p className="loading-text">Loading results...</p>
        </div>
      ) : results.length === 0 ? (
        <div className="empty-state">No bills found.</div>
      ) : (
        <div className="billing-grid">
          {results.map((r: any) => (
            <div key={r.id} className="billing-card">
              <div className="billing-header">
                <h3 className="billing-subtitle">
                  Bill for {r.year} / {r.month}
                </h3>
                <span className={`status-badge ${r.status.toLowerCase()}`}>
                  {r.status === 'manual_upload' ? 'Manual Upload' : r.status}
                </span>
              </div>

              <div className="billing-details">
                <p>
                  <strong>Date:</strong> {r.run_time}
                </p>
                {r.status === 'manual_upload' && (
                  <p>
                    <strong>Type:</strong> Manually uploaded
                  </p>
                )}
              </div>

              <button
                onClick={() => handleDownloadPDF(r.azure_blob_url)}
                className="download-btn"
              >
                Download Bill
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleUploadManualPDF}
        uploading={uploading}
      />
    </div>
  );
};

export default BillingResults;
