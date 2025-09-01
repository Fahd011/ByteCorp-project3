/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { credentialsAPI } from "../services/api";
 // custom CSS file
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
    <div className="max-w-4xl mx-auto mt-8 p-6">
      <h2 className="text-3xl font-bold text-slate-800 mb-6 border-b-2 border-slate-200 pb-2">Billing Results</h2>

      {/* Manual PDF Upload Section */}
      <div className=" bg-slate-50 border border-slate-200 rounded-xl p-5 mb-6">
        <h3 className="text-xl font-semibold text-slate-700 mb-4 border-b border-slate-200 pb-2">Upload Manual PDF Bill</h3>
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={() => setShowUploadModal(true)}
            disabled={uploading}
            className="px-5 py-2.5 bg-blue-500 text-white text-sm font-medium rounded-lg cursor-pointer transition flex items-center gap-1.5 hover:bg-blue-600 hover:-translate-y-px disabled:bg-slate-400 disabled:cursor-not-allowed disabled:transform-none"
          >
            {uploading ? "Uploading..." : "📁 Upload PDF Bill"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center mt-8">
          <div className="border-4 border-slate-200 border-t-blue-500 rounded-full w-10 h-10 animate-spin mb-2.5"></div>
          <p className="text-base text-slate-500">Loading results...</p>
        </div>
      ) : results.length === 0 ? (
        <div className="bg-yellow-50 text-yellow-800 px-4 py-3 rounded-lg shadow-sm">No bills found.</div>
      ) : (
        <div className="grid gap-4">
          {results.map((r: any) => (
            <div key={r.id} className="billing-card bg-white border border-slate-200 rounded-xl p-4 shadow-sm transition hover:shadow-md">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-slate-700">
                  Bill for {r.year} / {r.month}
                </h3>
                <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${r.status.toLowerCase() === 'completed' ? 'bg-green-100 text-green-800' : r.status.toLowerCase() === 'failed' ? 'bg-red-100 text-red-800' : r.status.toLowerCase() === 'pending' ? 'bg-slate-100 text-slate-600' : r.status.toLowerCase() === 'manual_upload' ? 'bg-yellow-100 text-yellow-800' : 'bg-slate-100 text-slate-600'}`}>
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

              <button
                onClick={() => handleDownloadPDF(r.azure_blob_url)}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg cursor-pointer transition hover:bg-blue-700"
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
