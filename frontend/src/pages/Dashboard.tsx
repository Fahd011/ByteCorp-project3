import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Job, CreateJobData } from '../types';
import { jobsAPI } from '../services/api';
import ImportModal from '../components/ImportModal';
import JobCard from '../components/JobCard';

const Dashboard: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [error, setError] = useState('');
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is authenticated
    if (!isAuthenticated) {
      console.log('User not authenticated, redirecting to login');
      navigate('/login');
      return;
    }
    
    console.log('User is authenticated, loading jobs');
    loadJobs();
  }, [isAuthenticated, navigate]);

  // Refresh running jobs status every 5 seconds
  // useEffect(() => {
  //   const runningJobs = jobs.filter(job => job.status === 'running');
  //   console.log('Running jobs found:', runningJobs.length, runningJobs.map(j => j.id));
    
  //   if (runningJobs.length === 0) return;

  //   const interval = setInterval(() => {
  //     console.log('Refreshing job statuses...');
  //     runningJobs.forEach(job => {
  //       refreshJobStatus(job.id);
  //     });
  //   }, 5000);

  //   return () => clearInterval(interval);
  // }, [jobs]);

  const loadJobs = async () => {
    setIsLoading(true);
    try {
      const jobsData = await jobsAPI.getAllJobs();
      console.log('Loaded jobs:', jobsData);
      // Filter out completed jobs - they should only appear in bills
      const activeJobs = jobsData.filter(job => job.status !== 'completed');
      console.log('Active jobs after filtering:', activeJobs);
      setJobs(activeJobs);
    } catch (err: any) {
      setError('Failed to load jobs');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // const refreshJobStatus = async (jobId: string) => {
  //   try {
  //     console.log('Refreshing status for job:', jobId);
  //     const jobData = await jobsAPI.getJob(jobId);
  //     console.log('Refreshed job data:', jobData);
  //     setJobs(jobs.map(job => 
  //       job.id === jobId ? jobData : job
  //     ));
  //   } catch (err: any) {
  //     console.error('Failed to refresh job status:', err);
  //   }
  // };

  const handleCreateJob = async (jobData: CreateJobData) => {
    setIsLoading(true);
    try {
      const newJob = await jobsAPI.createJob(jobData);
      setJobs([newJob, ...jobs]);
      setIsModalOpen(false);
    } catch (err: any) {
      setError('Failed to create job');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunJob = async (jobId: string) => {
    console.log('=== HANDLE RUN JOB CALLED ===');
    console.log('JobId:', jobId);
    console.log('Current jobs:', jobs);
    console.log('IsLoading:', isLoading);
    
    setIsLoading(true);
    try {
      console.log('About to call jobsAPI.runJob...');
      const updatedJob = await jobsAPI.runJob(jobId);
      console.log('runJob API call successful, response:', updatedJob);
      
      // Update the job with the server response
      setJobs(jobs.map(job => 
        job.id === jobId ? updatedJob : job
      ));
      console.log('Jobs state updated');
    } catch (err: any) {
      console.error('=== ERROR IN HANDLE RUN JOB ===');
      console.error('Error details:', err);
      console.error('Error message:', err.message);
      console.error('Error response:', err.response);
      setError('Failed to run job');
    } finally {
      console.log('Setting isLoading to false');
      setIsLoading(false);
    }
  };

  const handleStopJob = async (jobId: string) => {
    setIsLoading(true);
    try {
      const updatedJob = await jobsAPI.stopJob(jobId);
      // Update the job with the server response
      setJobs(jobs.map(job => 
        job.id === jobId ? updatedJob : job
      ));
    } catch (err: any) {
      setError('Failed to stop job');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    setIsLoading(true);
    try {
      await jobsAPI.deleteJob(jobId);
      setJobs(jobs.filter(job => job.id !== jobId));
    } catch (err: any) {
      setError('Failed to delete job');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewResults = (jobId: string) => {
    // Navigate to bills page to view results
    window.location.href = '/bills';
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>Active Jobs Dashboard</h1>
        <button 
          onClick={() => setIsModalOpen(true)}
          style={styles.importButton}
        >
          + Import New Job
        </button>
      </div>

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

      {isLoading && jobs.length === 0 ? (
        <div style={styles.loading}>Loading jobs...</div>
      ) : jobs.length === 0 ? (
        <div style={styles.empty}>
          <h3>No active jobs</h3>
          <p>Create your first job by clicking the "Import New Job" button above.</p>
          <p style={styles.note}>Completed jobs can be viewed in the Bills section.</p>
        </div>
      ) : (
        <div style={styles.jobsGrid}>
          {jobs.map(job => (
            <JobCard
              key={job.id}
              job={job}
              onRun={handleRunJob}
              onStop={handleStopJob}
              onDelete={handleDeleteJob}
              onViewResults={handleViewResults}
              isLoading={isLoading}
            />
          ))}
        </div>
      )}

      <ImportModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateJob}
        isLoading={isLoading}
      />
    </div>
  );
};

const styles = {
  container: {
    padding: '2rem',
    marginLeft: '250px', // Account for sidebar
    marginTop: '80px', // Account for header
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '2rem',
  },
  title: {
    margin: 0,
    color: '#333',
  },
  importButton: {
    padding: '0.75rem 1.5rem',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '1rem',
    fontWeight: 'bold',
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
  note: {
    fontSize: '0.9rem',
    color: '#999',
    marginTop: '1rem',
  },
  jobsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
    gap: '1.5rem',
  },
};

export default Dashboard;
