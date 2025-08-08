import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

interface SidebarProps {
  isOpen?: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen = true }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/bills', label: 'Bills', icon: '📄' },
  ];

  return (
    <aside style={{
      ...styles.sidebar,
      transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
    }}>
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
    flexShrink: 0, // Prevent sidebar from shrinking
    overflow: 'auto',
    transition: 'transform 0.3s ease',
    position: 'fixed' as const,
    top: 0,
    left: 0,
    zIndex: 1001, // Above overlay
    paddingTop: '80px', // Account for header
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
