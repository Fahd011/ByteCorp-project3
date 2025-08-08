import React, { useState, useEffect } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth < 768) {
        setSidebarOpen(false);
      } else {
        setSidebarOpen(true);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div style={styles.container}>
      <Header onMenuClick={isMobile ? toggleSidebar : undefined} />
      <div style={styles.content}>
        <Sidebar isOpen={sidebarOpen} />
        <main style={{
          ...styles.main,
          marginLeft: isMobile ? '0' : '250px',
        }}>
          {children}
        </main>
        {isMobile && sidebarOpen && (
          <div 
            style={styles.overlay}
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    display: 'flex',
    flexDirection: 'column' as const,
  },
  content: {
    display: 'flex',
    flex: 1,
    position: 'relative' as const,
  },
  main: {
    flex: 1,
    padding: '2rem',
    minHeight: 'calc(100vh - 80px)',
    overflow: 'auto',
    transition: 'margin-left 0.3s ease',
    marginTop: '80px', // Account for header
  },
  overlay: {
    position: 'fixed' as const,
    top: '80px',
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    zIndex: 1000,
  },
};

export default Layout;
