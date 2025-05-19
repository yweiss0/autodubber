import { writable } from 'svelte/store';
import { fetchJobs } from './api';

// Jobs store
export const jobs = writable([]);

// Selected job for transcription editing
export const selectedJobForTranscription = writable(null);

// Load jobs from API
export const loadJobs = async () => {
  try {
    const jobsData = await fetchJobs();
    
    // Convert from object to array and sort by creation date (newest first)
    const jobsArray = Object.values(jobsData).sort((a, b) => 
      new Date(b.created_at) - new Date(a.created_at)
    );
    
    jobs.set(jobsArray);
    return jobsArray;
  } catch (error) {
    console.error('Error loading jobs:', error);
    return [];
  }
};

// Add a new job to the store
export const addJob = (job) => {
  jobs.update(currentJobs => [job, ...currentJobs]);
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