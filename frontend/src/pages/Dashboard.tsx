import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Job, CreateJobData } from "../types";
import { jobsAPI } from "../services/api";
import ImportModal from "../components/ImportModal";
import JobCard from "../components/JobCard";

const Dashboard: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingJobs, setLoadingJobs] = useState<Set<string>>(new Set());
  const [cooldownJobs, setCooldownJobs] = useState<Map<string, number>>(() => {
    // Load cooldown timers from localStorage on component mount
    const saved = localStorage.getItem("jobCooldowns");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        const now = Date.now();
        const validCooldowns = new Map();

        // Only keep cooldowns that haven't expired yet
        Object.entries(parsed).forEach(([jobId, endTime]) => {
          if (typeof endTime === "number" && endTime > now) {
            validCooldowns.set(jobId, endTime);
          }
        });

        return validCooldowns;
      } catch (error) {
        console.error(
          "Failed to parse cooldown data from localStorage:",
          error
        );
      }
    }
    return new Map();
  });
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [error, setError] = useState("");
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  // Helper function to save cooldown data to localStorage
  const saveCooldownsToStorage = (cooldowns: Map<string, number>) => {
    const cooldownObject: Record<string, number> = {};
    cooldowns.forEach((endTime, jobId) => {
      cooldownObject[jobId] = endTime;
    });
    localStorage.setItem("jobCooldowns", JSON.stringify(cooldownObject));
  };

  useEffect(() => {
    // Check if user is authenticated
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }

    loadJobs();
  }, [isAuthenticated, navigate]);

  // Update cooldown timers every second
  useEffect(() => {
    const interval = setInterval(() => {
      setCooldownJobs((prev) => {
        const now = Date.now();
        const newMap = new Map();

        prev.forEach((endTime, jobId) => {
          if (now < endTime) {
            newMap.set(jobId, endTime);
          }
          // If cooldown has expired, don't add it back to the map
        });

        // Save updated cooldowns to localStorage
        saveCooldownsToStorage(newMap);
        return newMap;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Refresh running jobs status every 5 seconds
  useEffect(() => {
    const runningJobs = jobs.filter((job) => job.status === "running");
    console.log(
      "Running jobs found:",
      runningJobs.length,
      runningJobs.map((j) => j.id)
    );

    if (runningJobs.length === 0) return;

    const interval = setInterval(async () => {
      console.log("Refreshing job statuses...");
      for (const job of runningJobs) {
        try {
          const realtimeData = await jobsAPI.getJobRealtimeStatus(job.id);
          console.log("Realtime data for job:", job.id, realtimeData);

          // Update job with real-time data
          setJobs((prevJobs) =>
            prevJobs.map((j) =>
              j.id === job.id
                ? { ...j, results_count: realtimeData.results_count }
                : j
            )
          );
        } catch (err: any) {
          console.error("Failed to get real-time status for job:", job.id, err);
        }
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [jobs]);

  const loadJobs = async () => {
    setIsLoading(true);
    try {
      const jobsData = await jobsAPI.getAllJobs();
      setJobs(jobsData);
    } catch (err: any) {
      setError("Failed to load jobs");
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
      setError("Failed to create job");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunJob = async (jobId: string) => {
    setLoadingJobs((prev) => new Set(prev).add(jobId));
    try {
      const updatedJob = await jobsAPI.runJob(jobId);

      // Update the job with the server response
      setJobs(jobs.map((job) => (job.id === jobId ? updatedJob : job)));
    } catch (err: any) {
      setError("Failed to run job");
      console.error(err);
    } finally {
      setLoadingJobs((prev) => {
        const newSet = new Set(prev);
        newSet.delete(jobId);
        return newSet;
      });
    }
  };

  const handleStopJob = async (jobId: string) => {
    setLoadingJobs((prev) => new Set(prev).add(jobId));
    try {
      const updatedJob = await jobsAPI.stopJob(jobId);
      // Update the job with the server response
      setJobs(jobs.map((job) => (job.id === jobId ? updatedJob : job)));

      // Start cooldown timer for this job
      const cooldownEndTime = Date.now() + 1800000; // 30 minutes (1800 seconds)
      const newCooldowns = new Map(cooldownJobs).set(jobId, cooldownEndTime);
      setCooldownJobs(newCooldowns);
      saveCooldownsToStorage(newCooldowns);

      // Set up timer to remove cooldown after 30 minutes
      setTimeout(() => {
        setCooldownJobs((prev) => {
          const newMap = new Map(prev);
          newMap.delete(jobId);
          saveCooldownsToStorage(newMap);
          return newMap;
        });
      }, 1800000);
    } catch (err: any) {
      setError("Failed to stop job");
      console.error(err);
    } finally {
      setLoadingJobs((prev) => {
        const newSet = new Set(prev);
        newSet.delete(jobId);
        return newSet;
      });
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    setLoadingJobs((prev) => new Set(prev).add(jobId));
    try {
      await jobsAPI.deleteJob(jobId);
      setJobs(jobs.filter((job) => job.id !== jobId));
    } catch (err: any) {
      setError("Failed to delete job");
      console.error(err);
    } finally {
      setLoadingJobs((prev) => {
        const newSet = new Set(prev);
        newSet.delete(jobId);
        return newSet;
      });
    }
  };

  const handleViewResults = (jobId: string) => {
    // Navigate to bills page to view results
    navigate("/bills");
  };

  const handleViewCredentials = async (jobId: string) => {
    setLoadingJobs((prev) => new Set(prev).add(jobId));
    try {
      const credentialsData = await jobsAPI.getJobCredentials(jobId);
      // Open the CSV file in a new tab
      window.open(credentialsData.csv_url, "_blank");
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError("No credentials file found for this job");
      } else {
        setError("Failed to load credentials file");
      }
      console.error(err);
    } finally {
      setLoadingJobs((prev) => {
        const newSet = new Set(prev);
        newSet.delete(jobId);
        return newSet;
      });
    }
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
          <button onClick={() => setError("")} style={styles.errorClose}>
            ✕
          </button>
        </div>
      )}

      {isLoading && jobs.length === 0 ? (
        <div style={styles.loading}>Loading jobs...</div>
      ) : jobs.length === 0 ? (
        <div style={styles.empty}>
          <h3>No active jobs</h3>
          <p>
            Create your first job by clicking the "Import New Job" button above.
          </p>
          <p style={styles.note}>
            Completed jobs can be viewed in the Bills section.
          </p>
        </div>
      ) : (
        <div style={styles.jobsGrid}>
          {jobs.map((job) => {
            const cooldownEndTime = cooldownJobs.get(job.id);
            const isInCooldown = Boolean(
              cooldownEndTime && Date.now() < cooldownEndTime
            );
            const remainingSeconds = cooldownEndTime
              ? Math.ceil((cooldownEndTime - Date.now()) / 1000)
              : 0;

            return (
              <JobCard
                key={job.id}
                job={job}
                onRun={handleRunJob}
                onStop={handleStopJob}
                onDelete={handleDeleteJob}
                onViewResults={handleViewResults}
                onViewCredentials={handleViewCredentials}
                isLoading={loadingJobs.has(job.id)}
                isInCooldown={isInCooldown}
                cooldownRemaining={remainingSeconds}
              />
            );
          })}
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
    padding: "2rem",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "2rem",
  },
  title: {
    margin: 0,
    color: "#333",
  },
  importButton: {
    padding: "0.75rem 1.5rem",
    backgroundColor: "#007bff",
    color: "white",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "1rem",
    fontWeight: "bold",
  },
  error: {
    backgroundColor: "#f8d7da",
    color: "#721c24",
    padding: "1rem",
    borderRadius: "4px",
    marginBottom: "1rem",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  errorClose: {
    backgroundColor: "transparent",
    border: "none",
    color: "#721c24",
    cursor: "pointer",
    fontSize: "1.2rem",
  },
  loading: {
    textAlign: "center" as const,
    padding: "2rem",
    color: "#666",
  },
  empty: {
    textAlign: "center" as const,
    padding: "3rem",
    color: "#666",
  },
  note: {
    fontSize: "0.9rem",
    color: "#999",
    marginTop: "1rem",
  },
  jobsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))",
    gap: "1.5rem",
  },
};

export default Dashboard;
