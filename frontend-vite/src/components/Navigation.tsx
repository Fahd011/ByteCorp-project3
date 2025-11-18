import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "react-hot-toast";
import { auditLogsAPI } from "../services/api";

const Navigation: React.FC = () => {
  const { logout } = useAuth();
  const location = useLocation();

  const handleLogout = () => {
    logout();
  };

  const handleDownloadLogs = async () => {
    try {
      const response = await auditLogsAPI.downloadCSV();
      const blob = new Blob([response.data], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("Audit logs downloaded successfully");
    } catch (error) {
      toast.error("Failed to download audit logs");
    }
  };

  return (
    <nav className="w-[250px] bg-slate-100 border-r border-slate-200 p-6 flex flex-col h-screen fixed left-0 top-0">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-800 m-0">Sagiliti</h1>
      </div>

      <ul className="list-none p-0 m-0 flex-1">
        <li className="mb-2">
          <Link
            to="/"
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 font-medium no-underline ${
              location.pathname === "/" 
                ? "bg-blue-500 text-white" 
                : "text-slate-500 hover:bg-slate-200 hover:text-slate-800"
            }`}
          >
            <span className="text-xl">🏠</span>
            Dashboard
          </Link>
        </li>
        <li className="mb-2">
          <Link
            to="/manual-bills"
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 font-medium no-underline ${
              location.pathname === "/manual-bills"
                ? "bg-blue-500 text-white"
                : "text-slate-500 hover:bg-slate-200 hover:text-slate-800"
            }`}
          >
            <span className="text-xl">📄</span>
            Manual Bill Extraction
          </Link>
        </li>
      </ul>

      <div>
        <button onClick={handleDownloadLogs} className="flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-200 hover:text-slate-800 rounded-lg transition-all duration-200 font-medium no-underline w-full text-left bg-transparent border-0 cursor-pointer">
          <span className="text-xl">📥</span>
          Download Logs
        </button>
        <button onClick={handleLogout} className="flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-200 hover:text-slate-800 rounded-lg transition-all duration-200 font-medium no-underline w-full text-left bg-transparent border-0 cursor-pointer">
          <span className="text-xl">🚪</span>
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navigation;
