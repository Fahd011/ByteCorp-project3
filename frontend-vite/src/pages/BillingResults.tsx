/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { credentialsAPI, pdfExtractionAPI } from "../services/api";
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
    <div className="max-w-[800px] my-8 mx-auto p-6">
      <h2 className="text-[1.75rem] font-bold text-slate-800 mb-6 border-b-2 border-slate-200 pb-2">Billing Results</h2>

      {loading ? (
        <div className="flex flex-col items-center mt-8">
          <div className="w-10 h-10 border-4 border-gray-200 border-t-blue-500 rounded-full animate-spin mb-2.5"></div>
          <p className="text-base text-slate-500">Loading results...</p>
        </div>
      ) : results.length === 0 ? (
        <div className="bg-amber-100 text-amber-900 py-3 px-4 rounded-lg shadow-sm">No bills found.</div>
      ) : (
        <div className="grid gap-4">
          {results.map((r: any) => (
            <div key={r.id} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm transition-all duration-200 hover:shadow-md">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-[1.1rem] font-semibold text-slate-700">
                  Bill for {r.year} / {r.month}
                </h3>
                <span className={`py-1 px-2.5 rounded-full text-[0.85rem] font-medium ${
                  r.status.toLowerCase() === "completed"
                    ? "bg-emerald-100 text-emerald-900"
                    : r.status.toLowerCase() === "failed"
                    ? "bg-red-100 text-red-800"
                    : r.status.toLowerCase() === "pending"
                    ? "bg-slate-100 text-slate-600"
                    : r.status.toLowerCase() === "manual_upload"
                    ? "bg-amber-100 text-amber-900"
                    : "bg-slate-100 text-slate-600"
                }`}>
                  {r.status === "manual_upload" ? "Manual Upload" : r.status}
                </span>
              </div>

              <div className="text-sm text-slate-500 mb-4">
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

              <div className="flex gap-3 flex-wrap">
                <button
                  onClick={() => handleDownloadPDF(r.azure_blob_url)}
                  className="py-2 px-4 bg-blue-600 text-white text-sm font-medium border-0 rounded-lg cursor-pointer transition-[background] duration-200 hover:bg-blue-800"
                >
                  Download Bill
                </button>

                {r.excel_blob_url && (
                  <button
                    onClick={() => handleExportToExcel(r)}
                    className="py-2 px-4 bg-emerald-700 text-white text-sm font-medium border-0 rounded-lg cursor-pointer transition-[background] duration-200 hover:bg-emerald-800"
                  >
                    Export to Excel
                  </button>
                )}
                {r.json_blob_url && (
                  <button
                    onClick={() => handleDownloadJSON(r)}
                    className="py-2 px-4 bg-amber-500 text-white text-sm font-medium border-0 rounded-lg cursor-pointer transition-[background] duration-200 hover:bg-amber-600"
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
