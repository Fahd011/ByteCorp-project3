import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Navigation: React.FC = () => {
  const { logout } = useAuth();
  // const location = useLocation();

  const handleLogout = () => {
    logout();
  };

  return (
    <nav className="nav">
      <div className="nav-header">
        <h1 className="nav-title">Sagility</h1>
      </div>

      <ul className="nav-menu">
        <li className="nav-item">
          <Link
            to="/"
            className="nav-link active"
            // className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
          >
            <span className="nav-icon">🏠</span>
            Dashboard
          </Link>
        </li>
      </ul>

      <div style={{ marginTop: "auto", paddingTop: "1rem" }}>
        <button
          onClick={handleLogout}
          className="nav-link"
          style={{ width: "100%", justifyContent: "flex-start" }}
        >
          <span className="nav-icon">🚪</span>
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navigation;
