import React, { useState, useEffect } from 'react';
import { Job, JobDetail } from '../types';
import { jobsAPI } from '../services/api';

const Bills: React.FC = () => {
  const [jobsWithResults, setJobsWithResults] = useState<Job[]>([]);
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
      // Show jobs that have results (completed, stopped, or error status with results)
      const jobsWithResults = jobsData.filter(job => 
        job.status === 'completed' || 
        job.status === 'stopped' || 
        job.status === 'error' ||
        job.results_count > 0
      );
      setJobsWithResults(jobsWithResults);
    } catch (err: any) {
      setError('Failed to load jobs with results');
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

  const handleDownloadFile = async (fileUrl: string, filename: string) => {
    try {
      console.log('Downloading from Supabase URL:', fileUrl);
      
      // Download the file from Supabase and create a blob with correct MIME type
      const response = await fetch(fileUrl);
      if (!response.ok) {
        throw new Error(`Failed to fetch PDF: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      const pdfBlob = new Blob([blob], { type: 'application/pdf' });
      const pdfUrl = URL.createObjectURL(pdfBlob);
      
      // Create download link
      const link = document.createElement('a');
      link.href = pdfUrl;
      link.download = filename;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the blob URL after a delay
      setTimeout(() => URL.revokeObjectURL(pdfUrl), 60000); // 1 minute
    } catch (error) {
      console.error('Error downloading file:', error);
      setError('Failed to download PDF file');
    }
  };

  const handleViewFile = async (fileUrl: string) => {
    try {
      console.log('Opening Supabase URL:', fileUrl);
      
      // Since we fixed the MIME type in upload, we can try direct opening first
      // If that fails, fall back to the blob method
      try {
        // Try direct opening first
        window.open(fileUrl, '_blank');
      } catch (directError) {
        console.log('Direct opening failed, using blob method:', directError);
        
        // Fallback: Download and create blob with correct MIME type
        const response = await fetch(fileUrl);
        if (!response.ok) {
          throw new Error(`Failed to fetch PDF: ${response.statusText}`);
        }
        
        const blob = await response.blob();
        const pdfBlob = new Blob([blob], { type: 'application/pdf' });
        const pdfUrl = URL.createObjectURL(pdfBlob);
        
        // Open the PDF in a new tab
        window.open(pdfUrl, '_blank');
        
        // Clean up the blob URL after a delay
        setTimeout(() => URL.revokeObjectURL(pdfUrl), 60000); // 1 minute
      }
    } catch (error) {
      console.error('Error opening file:', error);
      setError('Failed to open PDF file');
    }
  };

  const handleDeleteAllResults = async (jobId: string) => {
    if (!window.confirm('Are you sure you want to delete all results for this job? This action cannot be undone.')) {
      return;
    }

    setIsLoading(true);
    try {
      await jobsAPI.deleteAllResults(jobId);
      // Refresh the job details
      if (selectedJob && selectedJob.id === jobId) {
        const updatedJobDetail = await jobsAPI.getJobDetails(jobId);
        setSelectedJob(updatedJobDetail);
      }
      // Refresh the jobs list
      await loadCompletedJobs();
      setError('');
    } catch (err: any) {
      setError('Failed to delete all results');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteSingleResult = async (jobId: string, resultId: string) => {
    if (!window.confirm('Are you sure you want to delete this result? This action cannot be undone.')) {
      return;
    }

    setIsLoading(true);
    try {
      await jobsAPI.deleteSingleResult(jobId, resultId);
      // Refresh the job details
      if (selectedJob && selectedJob.id === jobId) {
        const updatedJobDetail = await jobsAPI.getJobDetails(jobId);
        setSelectedJob(updatedJobDetail);
      }
      setError('');
    } catch (err: any) {
      setError('Failed to delete result');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    if (!window.confirm('Are you sure you want to delete this entire job? This will delete the job and all its results. This action cannot be undone.')) {
      return;
    }

    setIsLoading(true);
    try {
      await jobsAPI.deleteJob(jobId);
      // Clear selected job if it was the deleted one
      if (selectedJob && selectedJob.id === jobId) {
        setSelectedJob(null);
      }
      // Refresh the jobs list
      await loadCompletedJobs();
      setError('');
    } catch (err: any) {
      setError('Failed to delete job');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteAllJobs = async () => {
    if (!window.confirm('Are you sure you want to delete ALL completed jobs? This will delete all jobs and their results. This action cannot be undone.')) {
      return;
    }

    setIsLoading(true);
    try {
      // Delete all jobs one by one
      const deletePromises = jobsWithResults.map(job => jobsAPI.deleteJob(job.id));
      await Promise.all(deletePromises);
      
      // Clear selected job
      setSelectedJob(null);
      // Refresh the jobs list
      await loadCompletedJobs();
      setError('');
    } catch (err: any) {
      setError('Failed to delete all jobs');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Bills & Results</h1>
      <p style={styles.description}>
        View jobs with results and their generated files.
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
        <div style={styles.loading}>Loading jobs with results...</div>
      ) : jobsWithResults.length === 0 ? (
        <div style={styles.empty}>
          <h3>No jobs with results</h3>
          <p>Jobs with results will appear here with their generated files.</p>
        </div>
      ) : (
        <div style={styles.content}>
          <div style={styles.jobsList}>
            <div style={styles.jobsHeader}>
              <h2 style={styles.sectionTitle}>Jobs with Results</h2>
              {jobsWithResults.length > 0 && (
                <button 
                  onClick={handleDeleteAllJobs}
                  style={styles.deleteAllJobsButton}
                  disabled={isLoading}
                >
                  Delete All Jobs
                </button>
              )}
            </div>
                            {jobsWithResults.map(job => (
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
                <div style={styles.jobActions}>
                  <button 
                    onClick={() => handleViewJobDetails(job.id)}
                    style={styles.viewButton}
                  >
                    View Results
                  </button>
                  <button 
                    onClick={() => handleDeleteJob(job.id)}
                    style={styles.deleteJobButton}
                    disabled={isLoading}
                  >
                    Delete Job
                  </button>
                </div>
              </div>
            ))}
          </div>

          {selectedJob && (
            <div style={styles.resultsPanel}>
              <div style={styles.resultsHeader}>
                <h2>Job Results</h2>
                <div style={styles.headerActions}>
                  <button 
                    onClick={() => handleDeleteAllResults(selectedJob.id)}
                    style={styles.deleteAllButton}
                    disabled={isLoading}
                  >
                    Delete All Results
                  </button>
                  <button 
                    onClick={() => setSelectedJob(null)}
                    style={styles.closeButton}
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div style={styles.resultsList}>
                {selectedJob.output && selectedJob.output.length > 0 ? (
                  selectedJob.output.map((result, index) => (
                    <div key={index} style={styles.resultItem}>
                      <div style={styles.resultInfo}>
                        <p style={styles.resultInfoText}><strong>Email:</strong> {result.email || 'N/A'}</p>
                        <p style={styles.resultInfoText}><strong>Status:</strong> {result.status}</p>
                        {result.error && <p style={styles.resultInfoText}><strong>Error:</strong> {result.error}</p>}
                        {result.file_url && <p style={styles.resultInfoText}><strong>PDF:</strong> Available</p>}
                      </div>
                      <div style={styles.resultActions}>
                        {result.file_url && (
                          <div style={styles.fileActions}>
                            <button 
                              onClick={() => handleViewFile(result.file_url!)}
                              style={styles.viewFileButton}
                            >
                              View PDF
                            </button>
                            <button 
                              onClick={() => handleDownloadFile(result.file_url!, `bill_${result.email || index}.pdf`)}
                              style={styles.downloadButton}
                            >
                              Download PDF
                            </button>
                          </div>
                        )}
                        <button 
                          onClick={() => handleDeleteSingleResult(selectedJob.id, result.id)}
                          style={styles.deleteResultButton}
                          disabled={isLoading}
                        >
                          Delete
                        </button>
                      </div>
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
    flexDirection: 'row' as const,
  },
  jobsList: {
    flex: 1,
  },
  jobsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
  },
  sectionTitle: {
    color: '#333',
    margin: 0,
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
  jobActions: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
  },
  deleteJobButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.875rem',
  },
  deleteAllJobsButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.875rem',
    fontWeight: 'bold',
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
  headerActions: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
  },
  closeButton: {
    backgroundColor: 'transparent',
    border: 'none',
    fontSize: '1.5rem',
    cursor: 'pointer',
    color: '#666',
  },
  deleteAllButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.875rem',
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
  resultActions: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
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
  deleteResultButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#dc3545',
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
