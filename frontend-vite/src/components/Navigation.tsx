import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Navigation: React.FC = () => {
  const { logout } = useAuth();
  // const location = useLocation();

  const handleLogout = () => {
    logout();
  };

  return (
    <nav className="w-64 bg-slate-100 border-r border-slate-200 p-6 flex flex-col h-screen fixed left-0 top-0">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-800 m-0">Sagility</h1>
      </div>

      <ul className="list-none p-0 m-0 flex-1">
        <li className="mb-2">
          <Link
            to="/"
            className="flex items-center gap-3 px-4 py-3 text-slate-500 no-underline rounded-lg transition-colors duration-200 font-medium hover:bg-slate-200 hover:text-slate-800"
          >
            <span className="text-xl">🏠</span>
            Dashboard
          </Link>
        </li>
      </ul>

      <div className="mt-auto pt-4">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-3 text-slate-500 no-underline rounded-lg transition-colors duration-200 font-medium hover:bg-slate-200 hover:text-slate-800 w-full justify-start"
        >
          <span className="text-xl">🚪</span>
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navigation;
