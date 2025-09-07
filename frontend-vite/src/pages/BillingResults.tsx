/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { credentialsAPI, pdfExtractionAPI } from "../services/api";
import "./BillingResults.css"; // custom CSS file
import toast from "react-hot-toast";
import UploadModal from "../components/UploadModal";

const BillingResults: React.FC = () => {
  const { cred_id: credId } = useParams();
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [extracting, setExtracting] = useState<string | null>(null);
  const [extractedData, setExtractedData] = useState<{ [key: string]: any }>(
    {}
  );
  const [showExtractedData, setShowExtractedData] = useState<string | null>(
    null
  );
  // const [extractingAll, setExtractingAll] = useState(false);

  useEffect(() => {
    fetchResults();
  }, [credId]);

  // Check for existing extraction results when results are loaded
  useEffect(() => {
    if (results.length > 0) {
      checkExistingExtractions();
    }
  }, [results]);

  const checkExistingExtractions = async () => {
    for (const result of results) {
      try {
        const response = await pdfExtractionAPI.getResults(result.id);
        if (response.data.results && response.data.results.length > 0) {
          // Data already extracted - just display it
          const extracted = response.data.results[0].extracted_data;
          setExtractedData((prev) => ({
            ...prev,
            [result.id]: extracted,
          }));
          console.log(
            `Found existing extraction for billing result ${result.id}`
          );
        } else {
          // No existing extraction - start auto-extraction
          console.log(
            `No existing extraction found for ${result.id}, starting auto-extraction...`
          );
          await handleExtractData(result);
        }
      } catch (error) {
        // No existing extraction found - start auto-extraction
        console.log(
          `No existing extraction for billing result ${result.id}, starting auto-extraction...`
        );
        await handleExtractData(result);
      }
    }
  };

  const handleExtractData = async (billingResult: any) => {
    setExtracting(billingResult.azure_blob_url);
    try {
      console.log("Extracting data for billing result:", billingResult);
      const response = await pdfExtractionAPI.extractData(billingResult);

      console.log("Extraction response:", response.data);
      toast.success("Data extracted successfully!");

      // Store the extracted data
      if (response.data.results && response.data.results.length > 0) {
        const extracted = response.data.results[0].extracted_data;
        setExtractedData((prev) => ({
          ...prev,
          [billingResult.id]: extracted,
        }));
        console.log("Extracted data:", extracted);
        console.log("Billing context:", response.data.billing_result);
      }
    } catch (error: any) {
      console.error("Extraction error:", error);
      toast.error(error.response?.data?.detail || "Failed to extract data");
    } finally {
      setExtracting(null);
    }
  };

  // const handleExtractAllData = async () => {
  //   setExtractingAll(true);
  //   const billsToExtract = results.filter((r) => !extractedData[r.id]);

  //   if (billsToExtract.length === 0) {
  //     toast.success("All bills have already been extracted!");
  //     setExtractingAll(false);
  //     return;
  //   }

  //   toast.success(`Starting extraction for ${billsToExtract.length} bills...`);

  //   for (let i = 0; i < billsToExtract.length; i++) {
  //     const bill = billsToExtract[i];
  //     try {
  //       console.log(
  //         `Extracting data for bill ${i + 1}/${billsToExtract.length}:`,
  //         bill
  //       );
  //       const response = await pdfExtractionAPI.extractData(bill);

  //       if (response.data.results && response.data.results.length > 0) {
  //         const extracted = response.data.results[0].extracted_data;
  //         setExtractedData((prev) => ({
  //           ...prev,
  //           [bill.id]: extracted,
  //         }));
  //       }

  //       // Small delay between extractions to avoid overwhelming the server
  //       if (i < billsToExtract.length - 1) {
  //         await new Promise((resolve) => setTimeout(resolve, 1000));
  //       }
  //     } catch (error: any) {
  //       console.error(`Error extracting data for bill ${bill.id}:`, error);
  //       toast.error(
  //         `Failed to extract data for bill ${bill.year}/${bill.month}`
  //       );
  //     }
  //   }

  //   toast.success(`Completed extraction for ${billsToExtract.length} bills!`);
  //   setExtractingAll(false);
  // };

  const toggleExtractedData = (billingId: string) => {
    setShowExtractedData((prev) => (prev === billingId ? null : billingId));
  };

  const renderExtractedData = (data: any) => {
    if (!data) return <p className="no-data">No data available</p>;

    const flattenObject = (
      obj: any,
      prefix = ""
    ): Array<{ key: string; value: any; displayKey: string }> => {
      const result: Array<{ key: string; value: any; displayKey: string }> = [];

      for (const [k, v] of Object.entries(obj)) {
        const key = prefix ? `${prefix}.${k}` : k;
        const displayKey = k; // Only use the last element for display

        if (v && typeof v === "object" && !Array.isArray(v)) {
          result.push(...flattenObject(v, key));
        } else if (Array.isArray(v)) {
          if (v.length === 0) {
            result.push({ key, value: "No items", displayKey });
          } else {
            v.forEach((item, index) => {
              if (typeof item === "object") {
                result.push(...flattenObject(item, `${key}[${index}]`));
              } else {
                result.push({
                  key: `${key}[${index}]`,
                  value: item,
                  displayKey: `${k}[${index}]`,
                });
              }
            });
          }
        } else {
          result.push({ key, value: v, displayKey });
        }
      }

      return result;
    };

    const flattenedData = flattenObject(data);

    return (
      <div className="extracted-data-table">
        <div className="table-header">
          <div className="table-cell header-cell">Field</div>
          <div className="table-cell header-cell">Value</div>
        </div>
        {flattenedData.map((item, index) => (
          <div key={index} className="table-row">
            <div className="table-cell field-cell">
              {item.displayKey.replace(/_/g, " ")}
            </div>
            <div className="table-cell value-cell">
              {item.value === null || item.value === undefined ? (
                <span className="null-value">—</span>
              ) : (
                <span>{String(item.value)}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

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

  const handleExportToExcel = async (sessionId: string) => {
    try {
      const response = await pdfExtractionAPI.exportToExcel(sessionId);

      // Extract filename from Content-Disposition header
      const contentDisposition = response.headers['content-disposition'];
      let filename = `utility_bills_extraction_${sessionId}.xlsx`; // fallback
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
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
    } catch (error: any) {
      console.error("Export error:", error);
      toast.error(error.response?.data?.detail || "Failed to export to Excel");
    }
  };

  const handleUploadManualPDF = async (
    file: File,
    year: string,
    month: string
  ) => {
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

      {/* Extract All Data Section */}
      {/* {results.length > 0 && (
        <div className="extract-all-section">
          <h3 className="extract-all-title">Bulk Data Extraction</h3>
          <div className="extract-all-actions">
            <button
              onClick={handleExtractAllData}
              disabled={
                extractingAll ||
                results.filter((r) => !extractedData[r.id]).length === 0
              }
              className="extract-all-btn"
            >
              {extractingAll
                ? "Extracting All..."
                : `Extract All Data (${
                    results.filter((r) => !extractedData[r.id]).length
                  } bills)`}
            </button>
            <div className="extract-all-info">
              {results.filter((r) => extractedData[r.id]).length} of{" "}
              {results.length} bills already extracted
            </div>
          </div>
        </div>
      )} */}

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

                {/* Show extracting button when extraction is in progress */}
                {extracting === r.azure_blob_url && (
                  <button className="extract-btn" disabled>
                    Extracting Data...
                  </button>
                )}

                {/* Show view data and export buttons when data is extracted */}
                {extractedData[r.id] && (
                  <>
                    <button
                      onClick={() => toggleExtractedData(r.id)}
                      className="view-data-btn"
                    >
                      {showExtractedData === r.id ? "Hide Data" : "View Data"}
                    </button>
                    <button
                      onClick={() => handleExportToExcel(r.id)}
                      className="export-btn"
                    >
                      Export to Excel
                    </button>
                  </>
                )}
              </div>

              {/* Extracted Data Section */}
              {showExtractedData === r.id && extractedData[r.id] && (
                <div className="extracted-data-section">
                  <h4>Extracted Data:</h4>
                  {renderExtractedData(extractedData[r.id])}
                </div>
              )}
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
