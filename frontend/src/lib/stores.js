import { writable } from 'svelte/store';
import { fetchJobs, fetchJob } from './api';
import { browser } from '$app/environment';

// Constants for local storage
const RECENT_JOBS_KEY = 'autodubber_recent_jobs';
const MAX_RECENT_JOBS = 20;

// Load recent job IDs from local storage
const loadRecentJobIds = () => {
  if (!browser) return [];
  try {
    const recentJobs = JSON.parse(localStorage.getItem(RECENT_JOBS_KEY) || '[]');
    return Array.isArray(recentJobs) ? recentJobs : [];
  } catch (e) {
    console.error('Error loading recent jobs from localStorage:', e);
    return [];
  }
};

// Save recent job IDs to local storage
const saveRecentJobIds = (jobIds) => {
  if (!browser) return;
  try {
    // Keep only the most recent MAX_RECENT_JOBS jobs
    const recentJobs = jobIds.slice(0, MAX_RECENT_JOBS);
    localStorage.setItem(RECENT_JOBS_KEY, JSON.stringify(recentJobs));
  } catch (e) {
    console.error('Error saving recent jobs to localStorage:', e);
  }
};

// Jobs store
export const jobs = writable([]);

// Store for tracking if jobs are currently loading
export const jobsLoading = writable(false);

// Selected job for transcription editing
export const selectedJobForTranscription = writable(null);

// Load jobs from API
export const loadJobs = async () => {
  jobsLoading.set(true);
  try {
    // First try to get all jobs from the API
    const jobsData = await fetchJobs();
    
    // Convert from object to array and sort by creation date (newest first)
    const jobsArray = Object.values(jobsData).sort((a, b) => 
      new Date(b.created_at) - new Date(a.created_at)
    );
    
    // If we didn't get any jobs from the API or got an error,
    // try to load individual jobs from the recent jobs list
    if (jobsArray.length === 0) {
      const recentJobIds = loadRecentJobIds();
      console.log(`No jobs returned from API. Trying to load ${recentJobIds.length} recent jobs from local storage.`);
      
      if (recentJobIds.length > 0) {
        const loadedJobs = [];
        
        // Try to load each job individually
        for (const jobId of recentJobIds) {
          try {
            const job = await fetchJob(jobId);
            if (job && job.job_id) {
              loadedJobs.push(job);
            }
          } catch (err) {
            console.warn(`Could not load job ${jobId}:`, err);
          }
        }
        
        if (loadedJobs.length > 0) {
          // Sort by creation date (newest first)
          loadedJobs.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          jobs.set(loadedJobs);
          jobsLoading.set(false);
          return loadedJobs;
        }
      }
    }
    
    jobs.set(jobsArray);
    jobsLoading.set(false);
    return jobsArray;
  } catch (error) {
    console.error('Error loading jobs:', error);
    
    // On error, try to load individual jobs from recent list
    try {
      const recentJobIds = loadRecentJobIds();
      console.log(`Error loading jobs from API. Trying to load ${recentJobIds.length} recent jobs from local storage.`);
      
      if (recentJobIds.length > 0) {
        const loadedJobs = [];
        
        // Try to load each job individually
        for (const jobId of recentJobIds) {
          try {
            const job = await fetchJob(jobId);
            if (job && job.job_id) {
              loadedJobs.push(job);
            }
          } catch (err) {
            console.warn(`Could not load job ${jobId}:`, err);
          }
        }
        
        if (loadedJobs.length > 0) {
          // Sort by creation date (newest first)
          loadedJobs.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          jobs.set(loadedJobs);
          jobsLoading.set(false);
          return loadedJobs;
        }
      }
    } catch (e) {
      console.error('Error loading recent jobs:', e);
    }
    
    jobsLoading.set(false);
    return [];
  }
};

// Add a new job to the store
export const addJob = (job) => {
  if (!job || !job.job_id) return;
  
  jobs.update(currentJobs => [job, ...currentJobs]);
  
  // Add to recent jobs in local storage
  if (browser) {
    const recentJobIds = loadRecentJobIds();
    // Remove this job ID if it already exists to avoid duplicates
    const filteredIds = recentJobIds.filter(id => id !== job.job_id);
    // Add to the beginning of the array
    saveRecentJobIds([job.job_id, ...filteredIds]);
  }
};

// Update a job in the store
export const updateJob = (updatedJob) => {
  console.log(`Updating job in store: ${updatedJob.job_id}`, {
    status: updatedJob.status,
    progress: updatedJob.progress,
    current_activity: updatedJob.current_activity
  });
  
  if (!updatedJob || !updatedJob.job_id) {
    console.error("Attempted to update job with invalid data:", updatedJob);
    return;
  }
  
  jobs.update(currentJobs => {
    // Find the job in the current list
    const existingJobIndex = currentJobs.findIndex(job => job.job_id === updatedJob.job_id);
    
    // If job doesn't exist, add it
    if (existingJobIndex === -1) {
      console.log(`Job ${updatedJob.job_id} not found in store, adding it`);
      
      // Also add to recent jobs in local storage
      if (browser) {
        const recentJobIds = loadRecentJobIds();
        // Remove this job ID if it already exists to avoid duplicates
        const filteredIds = recentJobIds.filter(id => id !== updatedJob.job_id);
        // Add to the beginning of the array
        saveRecentJobIds([updatedJob.job_id, ...filteredIds]);
      }
      
      return [updatedJob, ...currentJobs];
    }
    
    // Merge the updated job with the existing job to preserve any fields not in the update
    const existingJob = currentJobs[existingJobIndex];
    const mergedJob = {
      ...existingJob,
      ...updatedJob,
      // Ensure we have timestamp of when this update occurred
      _lastUpdated: Date.now()
    };
    
    // Create a new array with the updated job
    const newJobs = [...currentJobs];
    newJobs[existingJobIndex] = mergedJob;
    
    console.log(`Updated job ${updatedJob.job_id} in store, new status: ${mergedJob.status}`);
    return newJobs;
  });
};

// Categorize jobs for display
export const categorizedJobs = (jobsArray) => {
  const running = [];
  const completed = [];
  const failed = [];
  
  jobsArray.forEach(job => {
    if (job.status === 'error') {
      failed.push(job);
    } else if (job.status === 'completed') {
      completed.push(job);
    } else {
      running.push(job);
    }
  });
  
  return { running, completed, failed };
}; 