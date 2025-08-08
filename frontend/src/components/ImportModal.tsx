import React, { useState } from 'react';
import { CreateJobData } from '../types';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateJobData) => void;
  isLoading: boolean;
}

const ImportModal: React.FC<ImportModalProps> = ({ isOpen, onClose, onSubmit, isLoading }) => {
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [loginUrl, setLoginUrl] = useState('');
  const [billingUrl, setBillingUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (csvFile && loginUrl && billingUrl) {
      onSubmit({ csv: csvFile, login_url: loginUrl, billing_url: billingUrl });
      // Reset form
      setCsvFile(null);
      setLoginUrl('');
      setBillingUrl('');
    }
  };

  if (!isOpen) return null;

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <div style={styles.header}>
          <h2 style={styles.title}>Import New Job</h2>
          <button onClick={onClose} style={styles.closeButton}>
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>CSV File:</label>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
              style={styles.fileInput}
              required
            />
          </div>
          
          <div style={styles.inputGroup}>
            <label style={styles.label}>Login URL:</label>
            <input
              type="url"
              value={loginUrl}
              onChange={(e) => setLoginUrl(e.target.value)}
              style={styles.input}
              placeholder="https://example.com/login"
              required
            />
          </div>
          
          <div style={styles.inputGroup}>
            <label style={styles.label}>Billing URL:</label>
            <input
              type="url"
              value={billingUrl}
              onChange={(e) => setBillingUrl(e.target.value)}
              style={styles.input}
              placeholder="https://example.com/billing"
              required
            />
          </div>
          
          <div style={styles.actions}>
            <button type="button" onClick={onClose} style={styles.cancelButton}>
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={isLoading || !csvFile || !loginUrl || !billingUrl}
              style={styles.submitButton}
            >
              {isLoading ? 'Creating...' : 'Create Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const styles = {
  overlay: {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  modal: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '2rem',
    width: '90%',
    maxWidth: '500px',
    maxHeight: '90vh',
    overflow: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.5rem',
  },
  title: {
    margin: 0,
    color: '#333',
  },
  closeButton: {
    backgroundColor: 'transparent',
    border: 'none',
    fontSize: '1.5rem',
    cursor: 'pointer',
    color: '#666',
  },
  form: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '1rem',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '0.5rem',
  },
  label: {
    fontWeight: 'bold',
    color: '#333',
  },
  input: {
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
  },
  fileInput: {
    padding: '0.5rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
  },
  actions: {
    display: 'flex',
    gap: '1rem',
    marginTop: '1rem',
  },
  cancelButton: {
    padding: '0.75rem 1.5rem',
    backgroundColor: '#6c757d',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1rem',
  },
  submitButton: {
    padding: '0.75rem 1.5rem',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1rem',
    flex: 1,
  },
};

export default ImportModal;
