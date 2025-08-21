import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { Users, FileText, Clock, CheckCircle, Plus, Play, Square, Upload, X, Trash2, Calendar, Download } from 'lucide-react';
import { credentialsAPI, schedulingAPI } from '../services/api';
import { formatDate } from '../utils/helpers';

const Dashboard = () => {
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [formData, setFormData] = useState({
    csvFile: null,
    loginUrl: '',
    billingUrl: '',
  });

  useEffect(() => {
    fetchCredentials();
  }, []);

  const fetchCredentials = async () => {
    try {
      const response = await credentialsAPI.getAll();
      setCredentials(response.data || []);
    } catch (error) {
      toast.error('Failed to load credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'text/csv') {
      setFormData({ ...formData, csvFile: file });
    } else {
      toast.error('Please select a valid CSV file');
    }
  };

  const handleCreateSession = async (e) => {
    e.preventDefault();
    
    if (!formData.csvFile) {
      toast.error('Please select a CSV file');
      return;
    }

    if (!formData.loginUrl || !formData.billingUrl) {
      toast.error('Please fill in all required fields');
      return;
    }

    setUploading(true);
    
    try {
      const uploadData = new FormData();
      uploadData.append('csv_file', formData.csvFile);
      uploadData.append('login_url', formData.loginUrl);
      uploadData.append('billing_url', formData.billingUrl);

      const response = await credentialsAPI.upload(uploadData);
      toast.success(response.data.message);
      
      // Reset form and close modal
      setFormData({
        csvFile: null,
        loginUrl: '',
        billingUrl: '',
      });
      setShowModal(false);
      
      // Refresh credentials list
      fetchCredentials();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleAgentControl = async (credId, action) => {
    try {
      await credentialsAPI.controlAgent(credId, action);
      toast.success(`Agent ${action.toLowerCase()}`);
      fetchCredentials();
    } catch (error) {
      toast.error('Failed to control agent');
    }
  };

  const handleDelete = async (credId) => {
    try {
      await credentialsAPI.delete(credId);
      toast.success('Credential deleted');
      fetchCredentials();
    } catch (error) {
      toast.error('Failed to delete credential');
    }
  };

  const handleScheduleWeekly = async () => {
    try {
      await schedulingAPI.scheduleWeekly();
      toast.success('Scheduled all credentials to run weekly');
      fetchCredentials();
    } catch (error) {
      toast.error('Failed to schedule weekly runs');
    }
  };

  const handleDownloadPDF = async (credId, email) => {
    try {
      const response = await credentialsAPI.downloadPDF(credId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `bill_${email}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('PDF downloaded successfully');
    } catch (error) {
      toast.error('Failed to download PDF');
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'idle':
        return 'status-badge status-idle';
      case 'running':
        return 'status-badge status-running';
      case 'completed':
        return 'status-badge status-completed';
      case 'error':
        return 'status-badge status-error';
      default:
        return 'status-badge status-idle';
    }
  };

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1 className="dashboard-title">Dashboard</h1>
        <p className="dashboard-subtitle">
          Welcome to Sagility - Your billing automation platform
        </p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-title">Total Credentials</div>
          <div className="stat-value">{credentials.length}</div>
          <Users size={24} style={{ marginTop: '0.5rem', color: '#6b7280' }} />
        </div>

        <div className="stat-card">
          <div className="stat-title">Active Credentials</div>
          <div className="stat-value">{credentials.filter(c => c.last_state === 'running').length}</div>
          <Clock size={24} style={{ marginTop: '0.5rem', color: '#3b82f6' }} />
        </div>

        <div className="stat-card">
          <div className="stat-title">Completed Jobs</div>
          <div className="stat-value">{credentials.filter(c => c.last_state === 'completed').length}</div>
          <CheckCircle size={24} style={{ marginTop: '0.5rem', color: '#10b981' }} />
        </div>

        <div className="stat-card">
          <div className="stat-title">Failed Jobs</div>
          <div className="stat-value">{credentials.filter(c => c.last_state === 'error').length}</div>
          <FileText size={24} style={{ marginTop: '0.5rem', color: '#ef4444' }} />
        </div>
      </div>

      {/* Create Session Button */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, color: '#1f2937' }}>Credential Jobs</h2>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={handleScheduleWeekly}
              className="btn btn-secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <Calendar size={16} />
              Schedule Weekly
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="btn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <Plus size={16} />
              Create Session
            </button>
          </div>
        </div>
      </div>

      {/* Credentials Grid */}
      {credentials.length === 0 ? (
        <div className="card">
          <div style={{ textAlign: 'center', padding: '3rem' }}>
            <Upload size={48} style={{ color: '#6b7280', marginBottom: '1rem' }} />
            <h3 style={{ color: '#374151', marginBottom: '0.5rem' }}>No credentials found</h3>
            <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
              Create your first session to get started with billing automation
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="btn btn-primary"
            >
              Create First Session
            </button>
          </div>
        </div>
      ) : (
        <div className="credentials-grid">
          {credentials.map((cred) => (
            <div key={cred.id} className="credential-card">
              <div className="credential-header">
                <div className="credential-info">
                  <h3 className="credential-email">{cred.email}</h3>
                  {cred.client_name && (
                    <p className="credential-client">{cred.client_name}</p>
                  )}
                  {cred.utility_co_name && (
                    <p className="credential-utility">{cred.utility_co_name}</p>
                  )}
                </div>
                <span className={getStatusBadgeClass(cred.last_state)}>
                  {cred.last_state}
                </span>
              </div>
              
              <div className="credential-details">
                {cred.login_url && (
                  <p className="credential-url">
                    <strong>Login:</strong> <a href={cred.login_url} target="_blank" rel="noopener noreferrer" style={{ color: '#3b82f6', textDecoration: 'underline' }}>
                      {cred.login_url.length > 40 ? cred.login_url.substring(0, 40) + '...' : cred.login_url}
                    </a>
                  </p>
                )}
                {cred.billing_url && (
                  <p className="credential-url">
                    <strong>Billing:</strong> <a href={cred.billing_url} target="_blank" rel="noopener noreferrer" style={{ color: '#3b82f6', textDecoration: 'underline' }}>
                      {cred.billing_url.length > 40 ? cred.billing_url.substring(0, 40) + '...' : cred.billing_url}
                    </a>
                  </p>
                )}
                {cred.last_run_time && (
                  <p className="credential-time">
                    Last run: {formatDate(cred.last_run_time)}
                  </p>
                )}
                {cred.last_error && (
                  <p className="credential-error">
                    Error: {cred.last_error}
                  </p>
                )}
              </div>
              
              <div className="credential-actions">
                {cred.last_state !== 'running' && (
                  <button
                    onClick={() => handleAgentControl(cred.id, 'RUN')}
                    className="btn btn-success"
                    style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                  >
                    <Play size={14} style={{ marginRight: '0.25rem' }} />
                    Start
                  </button>
                )}
                
                {cred.last_state === 'running' && (
                  <button
                    onClick={() => handleAgentControl(cred.id, 'STOPPED')}
                    className="btn btn-danger"
                    style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                  >
                    <Square size={14} style={{ marginRight: '0.25rem' }} />
                    Stop
                  </button>
                )}
                {cred.uploaded_bill_url && (
                  <button
                    onClick={() => handleDownloadPDF(cred.id, cred.email)}
                    className="btn btn-info"
                    style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                  >
                    <Download size={14} style={{ marginRight: '0.25rem' }} />
                    Download PDF
                  </button>
                )}
                <button
                  onClick={() => handleDelete(cred.id)}
                  className="btn btn-danger"
                  style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                >
                  <Trash2 size={14} style={{ marginRight: '0.25rem' }} />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Session Modal */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>Create New Session</h2>
              <button
                onClick={() => setShowModal(false)}
                className="modal-close"
              >
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleCreateSession}>
              <div className="form-group">
                <label className="form-label">CSV File</label>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileChange}
                  className="form-input"
                  required
                />
                <small style={{ color: '#6b7280', marginTop: '0.25rem', display: 'block' }}>
                  CSV should have columns: client_name, utility_co_id, utility_co_name, cred_id, cred_user, cred_password
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Login URL</label>
                <input
                  type="url"
                  value={formData.loginUrl}
                  onChange={(e) => setFormData({ ...formData, loginUrl: e.target.value })}
                  className="form-input"
                  placeholder="https://example.com/login"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Billing URL</label>
                <input
                  type="url"
                  value={formData.billingUrl}
                  onChange={(e) => setFormData({ ...formData, billingUrl: e.target.value })}
                  className="form-input"
                  placeholder="https://example.com/billing"
                  required
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={uploading}
                >
                  {uploading ? 'Creating Session...' : 'Create Session'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
