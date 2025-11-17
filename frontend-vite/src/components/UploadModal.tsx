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
    <div className="fixed top-0 left-0 right-0 bottom-0 bg-black/50 flex justify-center items-center z-[1000]" onClick={handleClose}>
      <div className="bg-white rounded-xl p-0 max-w-[500px] w-[90%] max-h-[90vh] overflow-y-auto shadow-[0_20px_25px_-5px_rgba(0,0,0,0.1),0_10px_10px_-5px_rgba(0,0,0,0.04)]" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center p-5 px-6 border-b border-slate-200">
          <h2 className="m-0 text-xl font-semibold text-slate-800">Upload PDF Bill</h2>
          <button className="bg-transparent border-0 text-2xl cursor-pointer text-slate-500 p-1 rounded hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed" onClick={handleClose} disabled={uploading}>
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          <div className="mb-5">
            <label htmlFor="pdfFile" className="block mb-2 font-medium text-gray-700 text-sm">Select PDF File</label>
            <input
              type="file"
              id="pdfFile"
              accept=".pdf"
              onChange={handleFileChange}
              className="w-full p-3 border border-gray-300 rounded-lg text-sm transition-[border-color] duration-200 focus:outline-none focus:border-blue-500 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.1)] file:py-2 file:px-4 file:border file:border-gray-300 file:rounded-md file:bg-gray-50 file:text-gray-700 file:text-sm file:cursor-pointer file:mr-4 file:hover:bg-gray-100"
              required
              disabled={uploading}
            />

          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="mb-5">
              <label htmlFor="year" className="block mb-2 font-medium text-gray-700 text-sm">Year</label>
              <input
                type="number"
                id="year"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                min="1900"
                max="2100"
                className="w-full py-3.5 px-4 border-2 border-gray-200 rounded-xl text-sm font-medium bg-white transition-all duration-300 shadow-sm text-gray-700 hover:border-blue-500 hover:bg-blue-50/30 hover:shadow-[0_4px_12px_rgba(59,130,246,0.15),0_2px_4px_rgba(0,0,0,0.1)] hover:-translate-y-0.5 focus:outline-none focus:border-blue-500 focus:shadow-[0_0_0_4px_rgba(59,130,246,0.15),0_4px_12px_rgba(59,130,246,0.1)] focus:bg-blue-50/30 focus:-translate-y-0.5 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:opacity-70 disabled:border-gray-200 disabled:shadow-none disabled:translate-y-0"
                required
                disabled={uploading}
              />
            </div>

            <div className="mb-5">
              <label htmlFor="month" className="block mb-2 font-medium text-gray-700 text-sm">Month</label>
              <select
                id="month"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
                className="w-full py-3.5 px-4 border-2 border-gray-200 rounded-xl text-sm font-medium bg-white appearance-none cursor-pointer transition-all duration-300 shadow-sm text-gray-700 hover:border-blue-500 hover:bg-blue-50/30 hover:shadow-[0_4px_12px_rgba(59,130,246,0.15),0_2px_4px_rgba(0,0,0,0.1)] hover:-translate-y-0.5 focus:outline-none focus:border-blue-500 focus:shadow-[0_0_0_4px_rgba(59,130,246,0.15),0_4px_12px_rgba(59,130,246,0.1)] focus:bg-blue-50/30 focus:-translate-y-0.5 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:opacity-70 disabled:border-gray-200 disabled:shadow-none disabled:translate-y-0 [background-image:url('data:image/svg+xml,%3csvg xmlns=%27http://www.w3.org/2000/svg%27 fill=%27none%27 viewBox=%270 0 24 24%27 stroke=%27%236b7280%27%3e%3cpath stroke-linecap=%27round%27 stroke-linejoin=%27round%27 stroke-width=%272%27 d=%27M19 9l-7 7-7-7%27/%3e%3c/svg%3e')] [background-position:right_1rem_center] [background-repeat:no-repeat] [background-size:1.25em_1.25em]"
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
              className="py-2.5 px-5 border-0 rounded-md text-sm font-medium cursor-pointer bg-gray-100 text-gray-700 transition-all duration-200 hover:bg-gray-200 disabled:opacity-60 disabled:cursor-not-allowed"
              disabled={uploading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="py-2.5 px-5 border-0 rounded-md text-sm font-medium cursor-pointer bg-blue-500 text-white transition-all duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
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
