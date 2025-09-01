import React, { useState } from 'react';


interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File, year: string, month: string) => void;
  uploading: boolean;
}

const UploadModal: React.FC<UploadModalProps> = ({ isOpen, onClose, onUpload, uploading }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [year, setYear] = useState(new Date().getFullYear().toString());
  const [month, setMonth] = useState((new Date().getMonth() + 1).toString().padStart(2, '0'));

  const months = [
    { value: '01', label: 'January' },
    { value: '02', label: 'February' },
    { value: '03', label: 'March' },
    { value: '04', label: 'April' },
    { value: '05', label: 'May' },
    { value: '06', label: 'June' },
    { value: '07', label: 'July' },
    { value: '08', label: 'August' },
    { value: '09', label: 'September' },
    { value: '10', label: 'October' },
    { value: '11', label: 'November' },
    { value: '12', label: 'December' },
  ];

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
    } else if (file) {
      alert('Please select a PDF file');
    }
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (selectedFile) {
      onUpload(selectedFile, year, month);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setSelectedFile(null);
      setYear(new Date().getFullYear().toString());
      setMonth((new Date().getMonth() + 1).toString().padStart(2, '0'));
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex justify-center items-center z-50" onClick={handleClose}>
      <div className="bg-white rounded-xl p-0 max-w-lg w-11/12 max-h-[90vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center px-6 py-5 border-b border-slate-200">
          <h2 className="m-0 text-xl font-semibold text-slate-800">Upload PDF Bill</h2>
          <button className="bg-transparent border-none text-2xl cursor-pointer text-slate-500 p-1 rounded hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition" onClick={handleClose} disabled={uploading}>
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          <div className="mb-5">
            <label htmlFor="pdfFile" className="block mb-2 font-medium text-slate-700 text-sm">Select PDF File</label>
            <input
              type="file"
              id="pdfFile"
              accept=".pdf"
              onChange={handleFileChange}
              className="w-full px-4 py-3 border-2 border-slate-200 rounded-xl text-sm font-medium bg-white transition-all duration-300 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/15 hover:border-blue-500 hover:-translate-y-px focus:-translate-y-px shadow-sm hover:shadow-md disabled:bg-slate-50 disabled:text-slate-500 disabled:cursor-not-allowed disabled:opacity-60 file:px-4 file:py-2 file:border file:border-slate-300 file:rounded-md file:bg-slate-50 file:text-slate-700 file:text-sm file:font-medium file:cursor-pointer file:hover:bg-slate-100 file:transition-colors"
              required
              disabled={uploading}
            />

          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="mb-5">
              <label htmlFor="year" className="block mb-2 font-medium text-slate-700 text-sm">Year</label>
              <input
                type="number"
                id="year"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                min="1900"
                max="2100"
                className="w-full px-4 py-3 border-2 border-slate-200 rounded-xl text-sm font-medium bg-gradient-to-br from-white to-slate-50 transition focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/15 hover:border-blue-500 hover:-translate-y-px disabled:bg-gradient-to-br disabled:from-slate-50 disabled:to-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed disabled:opacity-70 disabled:border-slate-200"
                required
                disabled={uploading}
              />
            </div>

            <div className="mb-5">
              <label htmlFor="month" className="block mb-2 font-medium text-slate-700 text-sm">Month</label>
              <select
                id="month"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
                className="w-full px-4 py-3 pr-12 border-2 border-slate-200 rounded-xl text-sm font-medium bg-white appearance-none cursor-pointer transition-all duration-300 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/15 hover:border-blue-500 hover:-translate-y-px focus:-translate-y-px shadow-sm hover:shadow-md disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed disabled:opacity-70 disabled:border-slate-200"
                style={{ 
                  backgroundImage: "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%236b7280'%3e%3cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3e%3c/svg%3e\")",
                  backgroundPosition: "right 1rem center",
                  backgroundRepeat: "no-repeat",
                  backgroundSize: "1.25em 1.25em"
                }}
                required
                disabled={uploading}
              >
                {months.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-slate-200">
            <button
              type="button"
              onClick={handleClose}
              className="px-5 py-2.5 border-none rounded-md text-sm font-medium cursor-pointer bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed transition"
              disabled={uploading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2.5 border-none rounded-md text-sm font-medium cursor-pointer bg-blue-500 text-white hover:bg-blue-600 disabled:bg-slate-400 disabled:cursor-not-allowed transition"
              disabled={!selectedFile || uploading}
            >
              {uploading ? 'Uploading...' : 'Upload PDF'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadModal;
