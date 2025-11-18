/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useRef, ChangeEvent, FormEvent } from "react";
import { toast } from "react-hot-toast";
import { manualBillsAPI, providerAPI, credentialsAPI } from "../services/api";
import { Provider, ManualBill } from "../types";

const ManualBillExtraction: React.FC = () => {
  const [manualBills, setManualBills] = useState<ManualBill[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [formData, setFormData] = useState({
    pdfFiles: [] as File[],
    selectedProviderId: "",
  });

  // Add a ref to track if polling is active
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchManualBills();
    fetchProviders();
    
    // Cleanup only on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Add polling for processing bills (every 30 seconds)
  useEffect(() => {
    const hasProcessingBills = manualBills.some(
      (bill) => bill.status?.toLowerCase() === "processing"
    );

    if (hasProcessingBills && !pollingIntervalRef.current) {
      console.log("📊 Polling started (checking every 30 seconds)");
      pollingIntervalRef.current = setInterval(() => {
        console.log("🔄 Checking status...");
        fetchManualBills();
      }, 30000); // 30 seconds
    } else if (!hasProcessingBills && pollingIntervalRef.current) {
      console.log("⏹️ Polling stopped - all bills processed");
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, [manualBills]);

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
    const files = Array.from(e.target.files || []);
    const pdfFiles = files.filter(file => file.type === "application/pdf");
    
    if (pdfFiles.length !== files.length) {
      toast.error("Some files were skipped. Only PDF files are allowed.");
    }
    
    setFormData({ ...formData, pdfFiles: pdfFiles });
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

    if (formData.pdfFiles.length === 0) {
      toast.error("Please select at least one PDF file");
      return;
    }

    if (!formData.selectedProviderId) {
      toast.error("Please select a provider");
      return;
    }

    setUploading(true);

    try {
      const uploadData = new FormData();
      const isBulkUpload = formData.pdfFiles.length > 1;
      
      if (isBulkUpload) {
        // Bulk upload - multiple files
        formData.pdfFiles.forEach(file => {
          uploadData.append("pdf_files", file);
        });
        uploadData.append("provider_id", formData.selectedProviderId);

        const response = await manualBillsAPI.bulkUpload(uploadData);

        toast.success(
          `${response.data.uploaded_count} bills uploaded successfully. Extraction in progress.`,
          { duration: 5000 }
        );
      } else {
        // Single file upload
        uploadData.append("pdf_file", formData.pdfFiles[0]);
        uploadData.append("provider_id", formData.selectedProviderId);

        const response = await manualBillsAPI.upload(uploadData);
        toast.success(response.data.message || "Bill uploaded successfully");
      }

      // Reset form and close modal
      setFormData({
        pdfFiles: [],
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
    return <div className="flex justify-center items-center h-[200px] text-slate-500">Loading...</div>;
  }

  return (
    <div>
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-slate-800 m-0 mb-2">Manual Bill Extraction</h1>
        <p className="text-slate-500 text-base m-0">
          Upload bills manually for automatic data extraction
        </p>
        {manualBills.some((bill) => bill.status?.toLowerCase() === "processing") && (
          <div className="mt-4 py-3 px-4 bg-blue-50 border border-blue-300 rounded-lg flex items-center gap-2 text-sm text-blue-900">
            <span className="inline-block w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin"></span>
            <span>Bills are being processed... Status will update automatically every 30 seconds.</span>
          </div>
        )}
      </div>

      {/* Search Section */}
      <div className="flex justify-between items-center mb-8 gap-4">
        <div className="relative flex-1 max-w-[800px]">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-base">🔍</span>
          <input
            type="text"
            placeholder="Search by filename or provider..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full py-3 pr-4 pl-10 border border-gray-300 rounded-lg text-sm bg-white transition-[border-color] duration-200 box-border focus:outline-none focus:border-blue-500 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.1)]"
          />
        </div>
        <div className="text-slate-500 text-sm whitespace-nowrap">
          Showing {filteredBills.length} of {manualBills.length} bills
        </div>
      </div>

      {/* Upload Bill Button */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex gap-4">
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-6 py-3 border-0 rounded-lg font-medium text-sm cursor-pointer transition-all duration-200 no-underline bg-blue-500 text-white hover:bg-blue-600"
          >
            ➕ Upload Bill
          </button>
        </div>
      </div>

      {/* Bills Grid */}
      {filteredBills.length === 0 ? (
        <div className="text-center p-12 bg-white rounded-xl border border-slate-200">
          <span className="text-gray-500 mb-4 text-5xl block">
            📄
          </span>
          <h3 className="text-gray-700 mb-2">
            {searchTerm ? "No matching bills found" : "No bills uploaded yet"}
          </h3>
          <p className="text-gray-500 mb-6">
            {searchTerm
              ? "Try adjusting your search terms"
              : "Get started by uploading your first bill for extraction."}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setShowModal(true)}
              className="inline-flex items-center gap-2 px-6 py-3 border-0 rounded-lg font-medium text-sm cursor-pointer transition-all duration-200 no-underline bg-blue-500 text-white hover:bg-blue-600"
            >
              Upload Bill
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(350px,1fr))] gap-6 mt-8">
          {filteredBills.map((bill) => (
            <div key={bill.id} className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 transition-all duration-200 hover:shadow-md">
              <div className="flex justify-between items-center gap-3 mb-4">
                <h3 
                  className="font-semibold text-slate-800 m-0 text-base leading-normal flex-1 min-w-0 truncate"
                  title={bill.original_filename || "Unnamed Bill"}
                >
                  {bill.original_filename || "Unnamed Bill"}
                </h3>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium capitalize flex items-center gap-1 flex-shrink-0 ${
                    getStatusBadgeClass(bill.status) === "status-running"
                      ? "bg-emerald-100 text-emerald-800"
                      : getStatusBadgeClass(bill.status) === "status-completed"
                      ? "bg-emerald-100 text-emerald-800"
                      : getStatusBadgeClass(bill.status) === "status-error"
                      ? "bg-red-100 text-red-600"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  ⏰ {bill.status}
                </span>
              </div>

              <div className="flex justify-between items-center mb-4">
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${
                    getProviderBadgeClass(bill.provider_name || "") === "provider-energy"
                      ? "bg-amber-100 text-amber-800"
                      : getProviderBadgeClass(bill.provider_name || "") === "provider-gas"
                      ? "bg-orange-200 text-orange-900"
                      : "bg-blue-100 text-blue-800"
                  }`}
                >
                  {getProviderIcon(bill.provider_name || "")}{" "}
                  {bill.provider_name || "Unknown Provider"}
                </span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 mb-4">
                <span className="text-slate-500 text-sm leading-normal m-0">
                  Uploaded: {bill.month} {bill.year}
                </span>
              </div>

              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => handleDownload(bill.azure_blob_url, "pdf")}
                  className="px-6 py-3 text-sm font-semibold flex-1 min-w-0 justify-center bg-blue-500 border-0 rounded-lg text-white cursor-pointer transition-all duration-200 hover:bg-blue-600 hover:-translate-y-0.5"
                  title="Download PDF"
                >
                  📄 PDF
                </button>
                {bill.excel_blob_url && (
                  <button
                    onClick={() => handleDownload(bill.excel_blob_url!, "xlsx")}
                    className="px-6 py-3 text-sm font-semibold flex-1 min-w-0 justify-center bg-emerald-600 border-0 rounded-lg text-white cursor-pointer transition-all duration-200 hover:bg-emerald-700 hover:-translate-y-0.5"
                    title="Download Excel"
                  >
                    📊 Excel
                  </button>
                )}
                {bill.json_blob_url && (
                  <button
                    onClick={() => handleDownload(bill.json_blob_url!, "json")}
                    className="px-6 py-3 text-sm font-semibold flex-1 min-w-0 justify-center bg-amber-500 border-0 rounded-lg text-white cursor-pointer transition-all duration-200 hover:bg-amber-600 hover:-translate-y-0.5"
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
        <div className="fixed top-0 left-0 right-0 bottom-0 bg-black/50 flex justify-center items-center z-[1000]" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-xl p-8 w-[90%] max-w-[500px] shadow-[0_20px_25px_-5px_rgba(0,0,0,0.1),0_10px_10px_-5px_rgba(0,0,0,0.04)]" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-slate-800 m-0">Upload Bill</h2>
              <button
                onClick={() => setShowModal(false)}
                className="bg-transparent border-0 text-2xl cursor-pointer text-slate-500 p-0 w-8 h-8 flex items-center justify-center rounded-md hover:bg-slate-100 hover:text-slate-800"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleUploadBill}>
              <div className="mb-6">
                <label htmlFor="pdfFile" className="block font-medium text-gray-700 mb-2 text-sm">
                  PDF File(s)
                </label>
                <input
                  type="file"
                  id="pdfFile"
                  accept=".pdf"
                  multiple
                  onChange={handleFileChange}
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm transition-[border-color] duration-200 focus:outline-none focus:border-blue-500 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.1)] file:py-2 file:px-4 file:border file:border-gray-300 file:rounded-md file:bg-gray-50 file:text-gray-700 file:text-sm file:cursor-pointer file:mr-4 file:hover:bg-gray-100"
                  required
                />
                {formData.pdfFiles.length > 0 && (
                  <div className="mt-2 text-sm text-blue-500 font-medium">
                    📎 {formData.pdfFiles.length} file(s) selected
                    {formData.pdfFiles.length > 1 && (
                      <span className="block mt-1 text-slate-500 font-normal">
                        ℹ️ Multiple files will be processed in chunks of 10
                      </span>
                    )}
                  </div>
                )}
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
