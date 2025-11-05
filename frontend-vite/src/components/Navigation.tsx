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
    <nav className="nav">
      <div className="nav-header">
        <h1 className="nav-title">Sagiliti</h1>
      </div>

      <ul className="nav-menu">
        <li className="nav-item">
          <Link
            to="/"
            className={`nav-link ${location.pathname === "/" ? "active" : ""}`}
          >
            <span className="nav-icon">🏠</span>
            Dashboard
          </Link>
        </li>
        <li className="nav-item">
          <Link
            to="/manual-bills"
            className={`nav-link ${
              location.pathname === "/manual-bills" ? "active" : ""
            }`}
          >
            <span className="nav-icon">📄</span>
            Manual Bill Extraction
          </Link>
        </li>
      </ul>

      <div className="nav-footer">
        <button onClick={handleDownloadLogs} className="nav-link">
          <span className="nav-icon">📥</span>
          Download Logs
        </button>
        <button onClick={handleLogout} className="nav-link">
          <span className="nav-icon">🚪</span>
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navigation;
