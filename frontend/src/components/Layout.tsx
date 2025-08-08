import React from 'react';
import Header from './Header';
import Sidebar from './Sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div style={styles.container}>
      <Header />
      <Sidebar />
      <main style={styles.main}>
        {children}
      </main>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
  },
  main: {
    marginLeft: '250px', // Account for sidebar
    marginTop: '80px', // Account for header
    minHeight: 'calc(100vh - 80px)',
  },
};

export default Layout;
