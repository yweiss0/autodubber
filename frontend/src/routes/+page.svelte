<script>
  import { onMount, onDestroy } from 'svelte';
  import { jobs, loadJobs, addJob, updateJob, selectedJobForTranscription, jobsLoading } from '$lib/stores';
  import { createJobWebSocket } from '$lib/api';
  
  import ApiKeyInput from '$lib/components/ApiKeyInput.svelte';
  import VoiceSelector from '$lib/components/VoiceSelector.svelte';
  import FileUpload from '$lib/components/FileUpload.svelte';
  import JobCard from '$lib/components/JobCard.svelte';
  import TranscriptionEditor from '$lib/components/TranscriptionEditor.svelte';
  
  // State
  let apiKey = '';
  let selectedVoiceId = 'uYkKk3J4lEp7IHQ8CLBi'; // Default Justin voice
  let activeWebSockets = {};
  let showTranscriptionEditor = false;
  let transcriptionJob = null;
  let loading = true;
  let socketMessageCounts = {}; // Track WebSocket message counts per job
  let loadRetryCount = 0;
  const MAX_RETRIES = 3;
  
  // Debug log when apiKey changes
  $: console.log(`Main page apiKey updated (length: ${apiKey.length})`);
  
  // Helper function to determine stage status
  function getStageStatus(currentStatus, stage) {
    const stages = {
      'extracting_audio': 0,
      'transcribing': 1,
      'transcription_complete': 2,
      'transcription_confirmed': 2,
      'generating_tts': 3,
      'creating_voiceover': 4,
      'creating_video': 5,
      'completed': 6,
      'error': -1
    };
    
    const currentStageIndex = stages[currentStatus] || 0;
    const stageIndex = stages[stage] || 0;
    
    if (currentStatus === 'error') return 'bg-red-500 text-white';
    if (currentStatus === stage) return 'bg-blue-500 text-white';
    if (stageIndex < currentStageIndex) return 'bg-green-500 text-white';
    return 'bg-gray-200 text-gray-400';
  }
  
  // Helper function to determine stage icon
  function getStageIcon(currentStatus, stage) {
    const stages = {
      'extracting_audio': 0,
      'transcribing': 1,
      'transcription_complete': 2,
      'transcription_confirmed': 2,
      'generating_tts': 3,
      'creating_voiceover': 4,
      'creating_video': 5,
      'completed': 6,
      'error': -1
    };
    
    const currentStageIndex = stages[currentStatus] || 0;
    const stageIndex = stages[stage] || 0;
    
    if (currentStatus === stage) return 'spinner';
    if (stageIndex < currentStageIndex) return 'check';
    return 'dot';
  }
  
  // Handle file upload completion
  const handleUpload = (event) => {
    const { jobId } = event.detail;
    console.log(`File uploaded successfully, job ID: ${jobId}`);
    
    // Create WebSocket connection for this job
    connectToJobWebSocket(jobId);
    
    // Show a notification
    showNotification('success', 'Upload Complete', 'Your video is now being processed.');
  };
  
  // Status display mapping for notifications
  const statusMessages = {
    extracting_audio: "Extracting audio from your video",
    transcribing: "Transcribing audio with Whisper AI",
    transcription_complete: "Transcription ready for review",
    transcription_confirmed: "Transcription confirmed, generating voiceover",
    generating_tts: "Generating AI voiceover with ElevenLabs",
    creating_voiceover: "Assembling audio segments",
    creating_video: "Creating final video with new voiceover",
    adjusting_speed: "Adjusting audio speed",
    creating_adjusted_video: "Creating video with adjusted audio",
    completed: "Processing complete! Your video is ready to download",
    error: "Error during processing"
  };
  
  // Create WebSocket connection for a job
  const connectToJobWebSocket = (jobId) => {
    if (activeWebSockets[jobId]) {
      console.log(`WebSocket for job ${jobId} already exists, closing old one before creating new`);
      const oldSocket = activeWebSockets[jobId];
      try {
        oldSocket.close();
      } catch (e) {
        console.warn(`Error closing old socket for job ${jobId}:`, e);
      }
      delete activeWebSockets[jobId];
    }
    
    console.log(`Creating new WebSocket connection for job ${jobId}`);
    socketMessageCounts[jobId] = 0;
    
    const socket = createJobWebSocket(
      jobId,
      (data) => {
        // Increment the message count for this job
        socketMessageCounts[jobId] = (socketMessageCounts[jobId] || 0) + 1;
        
        // Get the previous job state if it exists
        const previousJob = $jobs.find(j => j.job_id === data.job_id);
        const statusChanged = !previousJob || previousJob.status !== data.status;
        const activityChanged = !previousJob || previousJob.current_activity !== data.current_activity;
        const progressChanged = !previousJob || previousJob.progress !== data.progress;
        
        console.log(`WebSocket update for job ${jobId}:`, { 
          previousStatus: previousJob?.status,
          newStatus: data.status,
          statusChanged,
          currentActivity: data.current_activity,
          activityChanged,
          progress: data.progress,
          progressChanged,
          messageCount: socketMessageCounts[jobId],
          rawData: JSON.stringify(data)
        });
        
        // Force reactive update by creating a new object
        const jobUpdate = {
          ...data,
          _receivedTimestamp: Date.now()
        };
        
        // Always update the job data to ensure UI reflects latest state
        updateJob(jobUpdate);
        console.log("After update, job in store:", JSON.stringify($jobs.find(j => j.job_id === jobId)));
        
        // Show notification when status changes
        if (statusChanged && data.status in statusMessages) {
          // Prioritize showing notification for transcription that needs review
          if (data.status === 'transcription_complete') {
            console.log(`Showing notification for transcription review needed`);
            showNotification(
              'info', 
              'Action Required: Transcription Review', 
              'Your transcription is ready for review. Please edit if needed, then confirm to continue.',
              10000 // Show for longer (10 seconds)
            );
          }
          // Show notification for errors
          else if (data.status === 'error') {
            const notificationType = 'error';
            
            console.log(`Showing notification for error: ${data.status}`);
            showNotification(
              notificationType, 
              'Processing Error', 
              statusMessages[data.status]
            );
          }
          // We don't show notifications for other status updates anymore - rely on step display
        }
        
        // Don't show toast notifications for activity changes
        // We rely on the step component to show current activity
        
        // Don't show notifications for progress changes
        // We rely on the progress bar and step component
        
        // If job is completed or errored, close the WebSocket
        if (data.status === 'completed' || data.status === 'error') {
          console.log(`Job ${jobId} is now ${data.status}, closing WebSocket`);
          
          // Force a reload of the jobs list to ensure we have the latest data
          setTimeout(async () => {
            try {
              await loadJobs();
              console.log(`Reloaded jobs after job ${jobId} completed`);
            } catch (err) {
              console.error(`Error reloading jobs after completion:`, err);
            }
          }, 1000);
          
          socket.close();
          delete activeWebSockets[jobId];
          delete socketMessageCounts[jobId];
        }
      },
      () => {
        // Handle WebSocket close
        console.log(`WebSocket for job ${jobId} closed by server`);
        delete activeWebSockets[jobId];
        
        // Try to reconnect if the job is still in progress
        const job = $jobs.find(j => j.job_id === jobId);
        if (job && job.status !== 'completed' && job.status !== 'error') {
          console.log(`Attempting to reconnect WebSocket for job ${jobId}`);
          setTimeout(() => connectToJobWebSocket(jobId), 2000);
        }
      }
    );
    
    activeWebSockets[jobId] = socket;
    return socket;
  };
  
  // Handle edit transcription button click
  const handleEditTranscription = (event) => {
    const { jobId } = event.detail;
    
    // Find the job with this ID
    const job = $jobs.find(j => j.job_id === jobId);
    
    if (job && job.transcription) {
      transcriptionJob = job;
      showTranscriptionEditor = true;
    }
  };
  
  // Handle transcription update
  const handleTranscriptionUpdated = () => {
    showTranscriptionEditor = false;
    transcriptionJob = null;
    showNotification('success', 'Transcription Saved', 'Your edited transcription has been saved.');
  };
  
  // Show notification
  let notifications = [];
  
  function showNotification(type, title, message, duration = 5000) {
    const id = Date.now();
    notifications = [...notifications, { id, type, title, message }];
    
    // Auto-remove after specified duration (default 5 seconds)
    setTimeout(() => {
      notifications = notifications.filter(n => n.id !== id);
    }, duration);
  }
  
  // Remove notification
  function removeNotification(id) {
    notifications = notifications.filter(n => n.id !== id);
  }
  
  // Check WebSocket health and reconnect if needed
  function checkWebSocketHealth() {
    $jobs.forEach(job => {
      const isRunning = job.status !== 'completed' && job.status !== 'error';
      const hasActiveSocket = activeWebSockets[job.job_id];
      
      if (isRunning && !hasActiveSocket) {
        console.log(`Job ${job.job_id} is running but has no WebSocket connection. Reconnecting...`);
        connectToJobWebSocket(job.job_id);
      }
    });
  }
  
  // Load initial data
  onMount(async () => {
    console.log('Component mounted, loading jobs...');
    loading = true;
    
    try {
      await loadInitialData();
    } catch (e) {
      console.error('Error loading initial data:', e);
      showNotification('error', 'Error Loading Jobs', 'Could not load jobs. Please try refreshing the page.');
    } finally {
      loading = false;
    }
  });
  
  // Load initial data with retry logic
  const loadInitialData = async () => {
    try {
      const jobsData = await loadJobs();
      console.log(`Loaded ${jobsData.length} jobs`);
      
      // Create WebSocket connections for in-progress jobs
      const inProgressJobs = jobsData.filter(job => 
        job.status !== 'completed' && 
        job.status !== 'error'
      );
      
      if (inProgressJobs.length > 0) {
        console.log(`Found ${inProgressJobs.length} in-progress jobs, connecting WebSockets`);
        inProgressJobs.forEach(job => {
          connectToJobWebSocket(job.job_id);
        });
      }
      
      return jobsData;
    } catch (error) {
      console.error('Error loading initial data:', error);
      loadRetryCount++;
      
      if (loadRetryCount < MAX_RETRIES) {
        console.log(`Retrying load (attempt ${loadRetryCount + 1}/${MAX_RETRIES})...`);
        await new Promise(resolve => setTimeout(resolve, 1000 * loadRetryCount));
        return loadInitialData();
      } else {
        console.error(`Failed to load jobs after ${MAX_RETRIES} attempts`);
        throw error;
      }
    }
  };
  
  // Clean up on component destroy
  onDestroy(() => {
    console.log(`Cleaning up ${Object.keys(activeWebSockets).length} WebSocket connections`);
    // Close all WebSocket connections
    Object.values(activeWebSockets).forEach(socket => {
      try {
        socket.close();
      } catch (e) {
        console.warn("Error closing WebSocket:", e);
      }
    });
    activeWebSockets = {};
  });
  
  // Computed properties
  $: runningJobs = $jobs.filter(job => job.status !== 'completed' && job.status !== 'error');
  $: completedJobs = $jobs.filter(job => job.status === 'completed');
  $: failedJobs = $jobs.filter(job => job.status === 'error');
</script>

<svelte:head>
  <title>AutoVoiceOver - AI Video Voiceover</title>
</svelte:head>

<div class="max-w-6xl mx-auto">
  <div class="bg-white p-6 rounded-lg shadow-lg mb-8">
    <div class="flex items-center">
      <img src="/favicon.png" alt="Favicon" class="h-24 w-32 mr-2" />
      <h1 class="text-2xl font-bold text-gray-800 mb-0 flex items-center">AutoVoiceOver</h1>
    </div>
    <p class="text-gray-600 mb-2">
      Upload a video, and we'll replace the audio with a high-quality ElevenLabs voiceover.
    </p>
    <p class="text-gray-600 mb-4">
      Your video will be transcribed, and you'll have the opportunity to edit the transcription before the final voiceover is generated.
    </p>
  </div>
  
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Left Column: Settings -->
    <div class="lg:col-span-1 space-y-4">
      <ApiKeyInput bind:apiKey />
      <VoiceSelector apiKey={apiKey} bind:selectedVoiceId />
    </div>
    
    <!-- Right Column: Upload and Jobs List -->
    <div class="lg:col-span-2">
      <!-- File Upload Component -->
      <div class="mb-6">
        <FileUpload 
          apiKey={apiKey} 
          voiceId={selectedVoiceId} 
          on:uploaded={handleUpload} 
        />
      </div>
      
      <!-- Loading state -->
      {#if loading}
        <div class="bg-white p-6 rounded-lg shadow-md flex items-center justify-center">
          <svg class="animate-spin h-6 w-6 text-blue-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          <p class="text-gray-600">Loading jobs...</p>
        </div>
      {:else}
        <!-- Running Jobs -->
        <div class="mb-8">
          <h2 class="text-xl font-semibold text-gray-800 mb-3">Processing Jobs</h2>
          {#if runningJobs.length > 0}
            <div class="space-y-4">
              {#each runningJobs as job (job.job_id)}
                <JobCard job={job} on:editTranscription={handleEditTranscription} />
              {/each}
            </div>
          {:else}
            <div class="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
              <svg class="mx-auto h-12 w-12 text-gray-400 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <p class="text-gray-600">No videos are currently processing.</p>
            </div>
          {/if}
        </div>
        
        <!-- Completed Jobs -->
        <div class="mb-8">
          <h2 class="text-xl font-semibold text-gray-800 mb-3">Completed Jobs</h2>
          {#if completedJobs.length > 0}
            <div class="space-y-4">
              {#each completedJobs as job (job.job_id)}
                <JobCard job={job} />
              {/each}
            </div>
          {:else}
            <div class="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
              <svg class="mx-auto h-12 w-12 text-gray-400 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              <p class="text-gray-600">No videos have been processed yet.</p>
            </div>
          {/if}
        </div>
        
        <!-- Failed Jobs -->
        {#if failedJobs.length > 0}
          <div class="mb-8">
            <h2 class="text-xl font-semibold text-gray-800 mb-3">Failed Jobs</h2>
            <div class="space-y-4">
              {#each failedJobs as job (job.job_id)}
                <JobCard job={job} />
              {/each}
            </div>
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>

<!-- Notification system -->
{#if notifications.length > 0}
  <div class="fixed bottom-5 right-5 z-50 space-y-2">
    {#each notifications as { id, type, title, message }}
      <div class="notification bg-white rounded-lg shadow-lg p-4 max-w-md border-l-4 animate-slideIn flex items-start {
        type === 'success' ? 'border-green-500' : 
        type === 'error' ? 'border-red-500' : 
        type === 'processing' ? 'border-orange-500' :
        'border-blue-500'}">
        <div class="mr-3">
          {#if type === 'success'}
            <svg class="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          {:else if type === 'error'}
            <svg class="h-6 w-6 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          {:else if type === 'processing'}
            <svg class="h-6 w-6 text-orange-500 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
          {:else}
            <svg class="h-6 w-6 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          {/if}
        </div>
        <div class="flex-1">
          <h3 class="font-medium text-gray-900">{title}</h3>
          <p class="text-sm text-gray-600">{message}</p>
        </div>
        <button class="text-gray-400 hover:text-gray-600" on:click={() => removeNotification(id)}>
          <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    {/each}
  </div>
{/if}

<style>
  /* Animation for notifications */
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  .animate-slideIn {
    animation: slideIn 0.3s ease forwards;
  }
</style>

<!-- Transcription Editor Modal -->
{#if showTranscriptionEditor && transcriptionJob}
  <TranscriptionEditor 
    jobId={transcriptionJob.job_id} 
    segments={transcriptionJob.transcription}
    initialSpeedFactor={transcriptionJob.speed_factor || 1.0}
    on:transcriptionUpdated={handleTranscriptionUpdated}
    on:cancel={() => showTranscriptionEditor = false}
  />
{/if}
