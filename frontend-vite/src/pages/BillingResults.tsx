/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { credentialsAPI } from "../services/api";
import "./BillingResults.css"; // custom CSS file
import toast from "react-hot-toast";

const BillingResults: React.FC = () => {
  const { cred_id: credId } = useParams();
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
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

  const handleUploadManualPDF = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !credId) return;

    if (file.type !== "application/pdf") {
      toast.error("Please select a PDF file");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("pdf_file", file);

      await credentialsAPI.uploadManualPDF(credId, formData);
      toast.success("PDF uploaded successfully");
      
      // Refresh the page to show updated data
      window.location.reload();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to upload PDF");
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDownloadManualPDF = async () => {
    if (!credId) return;

    setDownloading(true);
    try {
      const response = await credentialsAPI.downloadManualPDF(credId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `manual_bill_${credId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Manual PDF downloaded successfully");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to download manual PDF");
    } finally {
      setDownloading(false);
    }
  };

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="billing-container">
      <h2 className="billing-title">Billing Results</h2>

      {/* Manual PDF Upload/Download Section */}
      <div className="manual-pdf-section">
        <h3 className="manual-pdf-title">Manual PDF Management</h3>
        <div className="manual-pdf-actions">
          <button
            onClick={triggerFileUpload}
            disabled={uploading}
            className="upload-btn"
          >
            {uploading ? "Uploading..." : "📁 Upload PDF"}
          </button>
          
          <button
            onClick={handleDownloadManualPDF}
            disabled={downloading}
            className="download-manual-btn"
          >
            {downloading ? "Downloading..." : "⬇️ Download Manual PDF"}
          </button>
        </div>
        
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleUploadManualPDF}
          style={{ display: "none" }}
        />
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
                  {r.status}
                </span>
              </div>

              <div className="billing-details">
                <p>
                  <strong>Date:</strong> {r.run_time}
                </p>
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
    </div>
  );
};

export default BillingResults;
