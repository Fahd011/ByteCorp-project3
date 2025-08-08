import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/bills', label: 'Bills', icon: '📄' },
  ];

  return (
    <aside style={styles.sidebar}>
      <nav style={styles.nav}>
        {menuItems.map((item) => (
          <button
            key={item.path}
            onClick={() => navigate(item.path)}
            style={{
              ...styles.navItem,
              ...(location.pathname === item.path ? styles.activeNavItem : {}),
            }}
          >
            <span style={styles.icon}>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
};

const styles = {
  sidebar: {
    width: '250px',
    backgroundColor: '#f8f9fa',
    borderRight: '1px solid #e0e0e0',
    height: '100vh',
    position: 'fixed' as const,
    left: 0,
    top: 0,
    paddingTop: '80px', // Account for header height
  },
  nav: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '0.5rem',
    padding: '1rem',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.75rem 1rem',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '1rem',
    color: '#666',
    transition: 'all 0.2s ease',
  },
  activeNavItem: {
    backgroundColor: '#007bff',
    color: 'white',
  },
  icon: {
    fontSize: '1.2rem',
  },
};

export default Sidebar;
