import React, { useState, useEffect } from 'react';
import { Job, JobDetail } from '../types';
import { jobsAPI } from '../services/api';

const Bills: React.FC = () => {
  const [completedJobs, setCompletedJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadCompletedJobs();
  }, []);

  const loadCompletedJobs = async () => {
    setIsLoading(true);
    try {
      const jobsData = await jobsAPI.getAllJobs();
      const completed = jobsData.filter(job => job.status === 'completed');
      setCompletedJobs(completed);
    } catch (err: any) {
      setError('Failed to load completed jobs');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewJobDetails = async (jobId: string) => {
    try {
      const jobDetail = await jobsAPI.getJobDetails(jobId);
      setSelectedJob(jobDetail);
    } catch (err: any) {
      setError('Failed to load job details');
      console.error(err);
    }
  };

  const handleDownloadFile = (fileUrl: string, filename: string) => {
    const link = document.createElement('a');
    link.href = fileUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleViewFile = (fileUrl: string) => {
    window.open(fileUrl, '_blank');
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Bills & Results</h1>
      <p style={styles.description}>
        View completed jobs and their generated files.
      </p>

      {error && (
        <div style={styles.error}>
          {error}
          <button 
            onClick={() => setError('')}
            style={styles.errorClose}
          >
            ✕
          </button>
        </div>
      )}

      {isLoading ? (
        <div style={styles.loading}>Loading completed jobs...</div>
      ) : completedJobs.length === 0 ? (
        <div style={styles.empty}>
          <h3>No completed jobs</h3>
          <p>Completed jobs will appear here with their generated files.</p>
        </div>
      ) : (
        <div style={styles.content}>
          <div style={styles.jobsList}>
            <h2 style={styles.sectionTitle}>Completed Jobs</h2>
            {completedJobs.map(job => (
              <div key={job.id} style={styles.jobItem}>
                <div style={styles.jobHeader}>
                  <h3 style={styles.jobTitle}>Job {job.id.slice(0, 8)}...</h3>
                  <span style={styles.jobDate}>
                    {new Date(job.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div style={styles.jobInfo}>
                  <p style={styles.jobInfoText}><strong>Login URL:</strong> {job.login_url}</p>
                  <p style={styles.jobInfoText}><strong>Billing URL:</strong> {job.billing_url}</p>
                  <p style={styles.jobInfoText}><strong>Results:</strong> {job.results_count} items</p>
                </div>
                <button 
                  onClick={() => handleViewJobDetails(job.id)}
                  style={styles.viewButton}
                >
                  View Results
                </button>
              </div>
            ))}
          </div>

          {selectedJob && (
            <div style={styles.resultsPanel}>
              <div style={styles.resultsHeader}>
                <h2>Job Results</h2>
                <button 
                  onClick={() => setSelectedJob(null)}
                  style={styles.closeButton}
                >
                  ✕
                </button>
              </div>
              <div style={styles.resultsList}>
                {selectedJob.output && selectedJob.output.length > 0 ? (
                  selectedJob.output.map((result, index) => (
                    <div key={index} style={styles.resultItem}>
                      <div style={styles.resultInfo}>
                        <p style={styles.resultInfoText}><strong>Email:</strong> {result.email}</p>
                        <p style={styles.resultInfoText}><strong>Status:</strong> {result.status}</p>
                        {result.error && <p style={styles.resultInfoText}><strong>Error:</strong> {result.error}</p>}
                      </div>
                      {result.filename && (
                        <div style={styles.fileActions}>
                          <button 
                            onClick={() => handleViewFile(result.filename!)}
                            style={styles.viewFileButton}
                          >
                            View File
                          </button>
                          <button 
                            onClick={() => handleDownloadFile(result.filename!, `result_${index}.pdf`)}
                            style={styles.downloadButton}
                          >
                            Download
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p style={styles.noResults}>No results available for this job.</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '2rem',
    marginLeft: '250px',
    marginTop: '80px',
  },
  title: {
    color: '#333',
    marginBottom: '0.5rem',
  },
  description: {
    color: '#666',
    marginBottom: '2rem',
  },
  error: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
    padding: '1rem',
    borderRadius: '4px',
    marginBottom: '1rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  errorClose: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#721c24',
    cursor: 'pointer',
    fontSize: '1.2rem',
  },
  loading: {
    textAlign: 'center' as const,
    padding: '2rem',
    color: '#666',
  },
  empty: {
    textAlign: 'center' as const,
    padding: '3rem',
    color: '#666',
  },
  content: {
    display: 'flex',
    gap: '2rem',
  },
  jobsList: {
    flex: 1,
  },
  sectionTitle: {
    color: '#333',
    marginBottom: '1rem',
  },
  jobItem: {
    backgroundColor: 'white',
    padding: '1.5rem',
    borderRadius: '8px',
    marginBottom: '1rem',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    border: '1px solid #e0e0e0',
  },
  jobHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
  },
  jobTitle: {
    margin: 0,
    color: '#333',
  },
  jobDate: {
    color: '#666',
    fontSize: '0.9rem',
  },
  jobInfo: {
    marginBottom: '1rem',
  },
  jobInfoText: {
    margin: '0.25rem 0',
    color: '#666',
  },
  viewButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.875rem',
  },
  resultsPanel: {
    flex: 1,
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    border: '1px solid #e0e0e0',
    maxHeight: '600px',
    overflow: 'auto',
  },
  resultsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
    borderBottom: '1px solid #e0e0e0',
    paddingBottom: '1rem',
  },
  closeButton: {
    backgroundColor: 'transparent',
    border: 'none',
    fontSize: '1.5rem',
    cursor: 'pointer',
    color: '#666',
  },
  resultsList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '1rem',
  },
  resultItem: {
    padding: '1rem',
    border: '1px solid #e0e0e0',
    borderRadius: '4px',
    backgroundColor: '#f8f9fa',
  },
  resultInfo: {
    marginBottom: '1rem',
  },
  resultInfoText: {
    margin: '0.25rem 0',
    color: '#333',
  },
  fileActions: {
    display: 'flex',
    gap: '0.5rem',
  },
  viewFileButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.875rem',
  },
  downloadButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.875rem',
  },
  noResults: {
    textAlign: 'center' as const,
    color: '#666',
    fontStyle: 'italic',
  },
};

export default Bills;
