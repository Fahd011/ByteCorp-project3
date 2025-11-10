/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { credentialsAPI, pdfExtractionAPI } from "../services/api";
import "./BillingResults.css"; // custom CSS file
import toast from "react-hot-toast";

const BillingResults: React.FC = () => {
  const { cred_id: credId } = useParams();
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

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

  const handleExportToExcel = async (result: any) => {
    try {
      // Check if we have an Excel blob URL in the database
      if (result.excel_blob_url) {
        // Download from Azure using the stored blob URL
        const response = await credentialsAPI.downloadExcel(
          result.excel_blob_url
        );

        // Extract filename from the blob URL or create one
        const filename =
          result.excel_blob_url.split("/").pop() ||
          `utility_bills_extraction_${result.id}.xlsx`;

        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

        toast.success("Excel file downloaded successfully!");
      } else {
        // Fallback to the old method if no Excel blob URL exists
        const response = await pdfExtractionAPI.exportToExcel(result.id);

        // Extract filename from Content-Disposition header
        const contentDisposition = response.headers["content-disposition"];
        let filename = `utility_bills_extraction_${result.id}.xlsx`; // fallback

        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(
            /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
          );
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1].replace(/['"]/g, "");
          }
        }

        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

        toast.success("Excel file downloaded successfully!");
      }
    } catch (error: any) {
      console.error("Export error:", error);
      toast.error(error.response?.data?.detail || "Failed to export to Excel");
    }
  };

  const handleDownloadJSON = async (result: any) => {
    try {
      if (result.json_blob_url) {
        const response = await credentialsAPI.downloadJSON(
          result.json_blob_url
        );

        const filename =
          result.json_blob_url.split("/").pop() ||
          `utility_bills_data_${result.id}.json`;

        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

        toast.success("JSON data downloaded successfully!");
      } else {
        toast.error("No JSON data available for this billing result");
      }
    } catch (error: any) {
      console.error("JSON download error:", error);
      toast.error("Failed to download JSON data");
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
                  {r.status === "manual_upload" ? "Manual Upload" : r.status}
                </span>
              </div>

              <div className="billing-details">
                <p>
                  <strong>Date:</strong>{" "}
                  {r.run_time ? new Date(r.run_time).toLocaleString() : "N/A"}
                </p>
                {r.status === "manual_upload" && (
                  <p>
                    <strong>Type:</strong> Manually uploaded
                  </p>
                )}
              </div>

              <div className="billing-actions">
                <button
                  onClick={() => handleDownloadPDF(r.azure_blob_url)}
                  className="download-btn"
                >
                  Download Bill
                </button>

                {r.excel_blob_url && (
                  <button
                    onClick={() => handleExportToExcel(r)}
                    className="export-btn"
                  >
                    Export to Excel
                  </button>
                )}
                {r.json_blob_url && (
                  <button
                    onClick={() => handleDownloadJSON(r)}
                    className="download-json-btn"
                    style={{ marginLeft: "8px" }}
                  >
                    Download JSON
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BillingResults;
