import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Home, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Navigation = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    {
      path: '/',
      label: 'Dashboard',
      icon: Home,
    },
  ];

  return (
    <nav className="nav">
      <div className="nav-header">
        <h1 className="nav-title">Sagility</h1>
      </div>
      
      <ul className="nav-menu">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <li key={item.path} className="nav-item">
              <NavLink
                to={item.path}
                className={({ isActive }) => 
                  `nav-link ${isActive ? 'active' : ''}`
                }
              >
                <Icon className="nav-icon" />
                {item.label}
              </NavLink>
            </li>
          );
        })}
      </ul>
      
      <div style={{ marginTop: 'auto', paddingTop: '2rem' }}>
        <button
          onClick={handleLogout}
          className="nav-link"
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer' }}
        >
          <LogOut className="nav-icon" />
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navigation;
