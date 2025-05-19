<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { getFilePath, API_BASE_URL, confirmTranscription } from '$lib/api';
  import { adjustAudioSpeed } from '$lib/api';
  import SpeedControlSlider from './SpeedControlSlider.svelte';
  import JobProgressSteps from './JobProgressSteps.svelte';

  // More detailed status display mapping
  const statusDisplay = {
    uploaded: "Uploaded, waiting to process...",
    extracting_audio: "Extracting Audio from Video...",
    transcribing: "Transcribing Audio with Whisper AI...",
    transcription_complete: "Transcription Ready for Review",
    transcription_confirmed: "Transcription Confirmed",
    generating_tts: "Generating AI Voiceover...",
    creating_voiceover: "Assembling Audio Segments...",
    creating_video: "Creating Final Video...",
    adjusting_speed: "Adjusting Audio Speed...",
    creating_adjusted_video: "Creating Video with Adjusted Audio...",
    completed: "Completed",
    error: "Error"
  };
  
  // Status color mapping
  const statusColor = {
    uploaded: "bg-blue-100 text-blue-800",
    extracting_audio: "bg-orange-100 text-orange-800",
    transcribing: "bg-orange-100 text-orange-800",
    transcription_complete: "bg-yellow-100 text-yellow-800",
    transcription_confirmed: "bg-yellow-100 text-yellow-800",
    generating_tts: "bg-orange-100 text-orange-800",
    creating_voiceover: "bg-orange-100 text-orange-800",
    creating_video: "bg-orange-100 text-orange-800",
    adjusting_speed: "bg-purple-100 text-purple-800",
    creating_adjusted_video: "bg-purple-100 text-purple-800",
    completed: "bg-green-100 text-green-800",
    error: "bg-red-100 text-red-800"
  };
  
  // Status icon mapping
  const statusIcon = {
    uploaded: "spinner",
    extracting_audio: "spinner",
    transcribing: "spinner",
    transcription_complete: "edit",
    transcription_confirmed: "spinner",
    generating_tts: "spinner",
    creating_voiceover: "spinner",
    creating_video: "spinner",
    adjusting_speed: "spinner",
    creating_adjusted_video: "spinner",
    completed: "check",
    error: "error"
  };
  
  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  // For tracking elapsed time for in-progress jobs
  let elapsedTime = '';
  let elapsedSeconds = 0;
  let estimatedTimeRemaining = '';
  let intervalId;
  let lastStatusUpdateTime = Date.now(); // Track when we last received a status update
  
  function updateElapsedTime() {
    if (!job.created_at) return;
    
    const created = new Date(job.created_at);
    const now = new Date();
    const diff = Math.floor((now - created) / 1000); // difference in seconds
    
    elapsedSeconds = diff;
    
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;
    
    elapsedTime = 
      (hours > 0 ? `${hours}h ` : '') + 
      (minutes > 0 ? `${minutes}m ` : '') + 
      `${seconds}s`;
      
    // Calculate estimated time remaining if we have progress > 0
    if (job.progress > 0 && job.progress < 100) {
      // Calculate total estimated time based on current progress and elapsed time
      const totalEstimatedSeconds = elapsedSeconds / (job.progress / 100);
      const remainingSeconds = Math.max(0, totalEstimatedSeconds - elapsedSeconds);
      
      // Format the remaining time
      const remainingHours = Math.floor(remainingSeconds / 3600);
      const remainingMinutes = Math.floor((remainingSeconds % 3600) / 60);
      const remainingSecs = Math.floor(remainingSeconds % 60);
      
      estimatedTimeRemaining = 
        (remainingHours > 0 ? `${remainingHours}h ` : '') + 
        (remainingMinutes > 0 ? `${remainingMinutes}m ` : '') + 
        `${remainingSecs}s`;
    } else {
      estimatedTimeRemaining = 'Calculating...';
    }
  }
  
  onMount(() => {
    updateElapsedTime();
    intervalId = setInterval(updateElapsedTime, 1000);
  });
  
  onDestroy(() => {
    if (intervalId) clearInterval(intervalId);
  });
  
  // Dispatch events to parent
  const dispatch = createEventDispatcher();
  
  // Props
  export let job;
  
  // Debug logging
  $: console.log(`JobCard received job:`, {
    jobId: job?.job_id,
    status: job?.status,
    progress: job?.progress,
    current_activity: job?.current_activity,
    hasTranscription: !!job?.transcription
  });
  
  // Watch for changes to the job object
  $: {
    if (job && job.status) {
      // Record when status updates happen
      lastStatusUpdateTime = Date.now();
    }
  }
  
  // Local state
  let videoUrl = '';
  let audioUrl = '';
  let srtUrl = '';
  let loadingPaths = false;
  let pathError = '';
  
  // Local state for speed control
  let speedFactor = job.speed_factor || 1.0;
  let isAdjustingSpeed = false;
  let speedAdjustmentError = '';
  
  // Watch for job updates to refresh the speed factor
  $: if (job.speed_factor) {
    speedFactor = job.speed_factor;
  }
  
  // Watch for job status to detect when speed adjustment is in progress
  $: isAdjustingSpeed = job.status === 'adjusting_speed' || job.status === 'creating_adjusted_video';
  
  // Status display mapping
  const statusLabels = {
    extracting_audio: "Extracting audio from video",
    transcribing: "Transcribing audio with Whisper AI",
    transcription_complete: "Transcription ready for review",
    transcription_confirmed: "Transcription confirmed, generating voiceover",
    generating_tts: "Generating AI voiceover with ElevenLabs",
    creating_voiceover: "Assembling audio segments",
    creating_video: "Creating final video with new voiceover",
    completed: "Processing complete",
    error: "Error during processing"
  };
  
  // Fetch file download URLs when component mounts and job is completed
  onMount(async () => {
    if (job.status === 'completed') {
      await loadFilePaths();
    }
  });
  
  // Watch for job status changes to load paths when job completes
  $: if (job.status === 'completed') {
    loadFilePaths();
  }
  
  // Function to load file download URLs from the backend
  async function loadFilePaths() {
    if (!job || !job.job_id) return;
    
    loadingPaths = true;
    pathError = '';
    
    try {
      // Load video path if available
      if (job.video_path) {
        // Use the download endpoint instead
        videoUrl = `${API_BASE_URL}/download/video/${job.job_id}`;
      }
      
      // Load audio path if available
      if (job.audio_path) {
        // Use the download endpoint instead
        audioUrl = `${API_BASE_URL}/download/audio/${job.job_id}`;
      }
      
      // Load SRT path if available
      if (job.srt_path) {
        // Use the download endpoint instead
        srtUrl = `${API_BASE_URL}/download/srt/${job.job_id}`;
      }
    } catch (error) {
      console.error('Error loading file paths:', error);
      pathError = error.message || 'Failed to load file paths';
    } finally {
      loadingPaths = false;
    }
  }
  
  // Handle edit transcription button click
  function handleEditTranscription() {
    dispatch('editTranscription', { jobId: job.job_id });
  }
  
  // Handle confirm transcription button click (skip editing)
  async function handleConfirmTranscription() {
    try {
      // Show confirmation message
      const confirmMsg = confirm("Confirm transcription without reviewing? This will use the original transcription generated by the AI.");
      
      if (confirmMsg) {
        // Update the job status message to indicate we're processing
        job.current_activity = "Confirming transcription...";
        
        // Call the API to confirm transcription
        await confirmTranscription(job.job_id);
        
        // No need to update UI - WebSocket will handle this
        console.log(`Transcription confirmed for job ${job.job_id} without editing`);
      }
    } catch (error) {
      console.error('Error confirming transcription:', error);
      alert(`Error confirming transcription: ${error.message}`);
    }
  }
  
  // Handle download buttons
  function handleDownload(type) {
    dispatch('download', { jobId: job.job_id, type });
  }
  
  // Compute display status
  $: displayStatus = statusDisplay[job.status] || job.status;
  $: statusBadgeClass = statusColor[job.status] || "bg-gray-100 text-gray-800";
  $: statusIconType = statusIcon[job.status] || "spinner";
  $: isCompleted = job.status === 'completed';
  $: isError = job.status === 'error';
  $: needsTranscriptionReview = job.status === 'transcription_complete';
  $: isProcessing = !isCompleted && !isError && job.status !== 'transcription_complete';
  // Only show speed control before processing starts - not on completed jobs
  $: showSpeedControl = false;
  
  // Define processing stages in order
  const processingStages = [
    { id: 'extracting_audio', label: 'Extract Audio' },
    { id: 'transcribing', label: 'Transcribe' },
    { id: 'transcription_complete', label: 'Review' },
    { id: 'transcription_confirmed', label: 'Confirm' },
    { id: 'generating_tts', label: 'Generate TTS' },
    { id: 'creating_voiceover', label: 'Assemble Audio' },
    { id: 'creating_video', label: 'Create Video' },
    { id: 'adjusting_speed', label: 'Adjust Speed' },
    { id: 'creating_adjusted_video', label: 'Adjust Video' },
    { id: 'completed', label: 'Complete' }
  ];
  
  // Helper to determine stage status
  function getStageStatus(stageId) {
    // Handle special case for initial status
    if (job.status === 'uploaded' && stageId === 'extracting_audio') return 'current';
    
    const stageIndex = processingStages.findIndex(stage => stage.id === stageId);
    const currentStageIndex = processingStages.findIndex(stage => stage.id === job.status);
    
    if (currentStageIndex === -1) return 'pending';
    
    if (stageIndex < currentStageIndex) return 'completed';
    if (stageIndex === currentStageIndex) return 'current';
    return 'pending';
  }
  
  // Handle speed change
  async function handleSpeedChange(event) {
    const newSpeed = event.detail.value;
    
    // If the speed is the same, do nothing
    if (newSpeed === job.speed_factor) return;
    
    speedAdjustmentError = '';
    
    try {
      // Call the API to adjust speed
      await adjustAudioSpeed(job.job_id, newSpeed);
      
      // Notification is handled automatically by the websocket update
    } catch (error) {
      console.error('Error adjusting speed:', error);
      speedAdjustmentError = error.message;
    }
  }
</script>

<div class="bg-white border rounded-lg overflow-hidden shadow-sm mb-4 transition-all">
  <div class="p-4">
    <div class="flex justify-between items-start">
      <div class="flex items-start flex-1">
        <!-- Status Icon -->
        <div class="mr-3 mt-1">
          {#if statusIconType === 'spinner'}
            <div class="w-8 h-8 flex items-center justify-center text-blue-600">
              <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
            </div>
          {:else if statusIconType === 'check'}
            <div class="w-8 h-8 flex items-center justify-center bg-green-100 text-green-800 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          {:else if statusIconType === 'error'}
            <div class="w-8 h-8 flex items-center justify-center bg-red-100 text-red-800 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
          {:else if statusIconType === 'edit'}
            <div class="w-8 h-8 flex items-center justify-center bg-yellow-100 text-yellow-800 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
          {/if}
        </div>
      
        <div class="flex-1">
          <h3 class="text-lg font-medium text-gray-800">{job.filename}</h3>
          <div class="text-sm text-gray-500 flex flex-col sm:flex-row sm:gap-4">
            <span>Created: {formatDate(job.created_at)}</span>
            {#if job.finished_at}
              <span>Finished: {formatDate(job.finished_at)}</span>
            {:else if isProcessing}
              <span class="text-blue-600">Running time: {elapsedTime}</span>
            {/if}
          </div>
          
          <div class="mt-1 flex items-center gap-2">
            <span class="px-2 py-1 text-xs font-medium rounded-full {statusBadgeClass}">
              {displayStatus}
            </span>
            {#if isProcessing}
              <span class="text-xs text-gray-500">
                <svg xmlns="http://www.w3.org/2000/svg" class="inline-block h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {elapsedTime}
              </span>
            {/if}
          </div>
        </div>
      </div>
    </div>
    
    <!-- Add steps visualization for all job states, more prominently displayed -->
    <div class="border-t border-b border-gray-200 bg-gray-50 py-4 px-3 mt-2">
      <JobProgressSteps {job} />
    </div>
    
    <!-- Detailed current activity message - only shown if not already visible in steps component -->
    {#if isProcessing && (!job.current_activity || job.current_activity.length === 0)}
      <div class="mt-3 mb-2">
        <div class="flex items-center bg-blue-50 p-4 rounded-lg border border-blue-200">
          <div class="mr-4 flex-shrink-0">
            <svg class="animate-spin h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
          </div>
          <div class="flex-1">
            <!-- Main stage as title -->
            <h4 class="text-base font-semibold text-blue-800">
              {statusDisplay[job.status] || job.status.replace(/_/g, ' ')}
            </h4>
          </div>
        </div>
      </div>
    {/if}
    
    {#if isProcessing}
      <div class="mt-4">
        <!-- Progress Bar -->
        <div class="relative pt-1">
          <div class="overflow-hidden h-2 mb-1 text-xs flex rounded bg-gray-200">
            <div class="w-0 bg-teal-500 rounded transition-all duration-300" style="width: {job.progress}%"></div>
          </div>
          <div class="flex justify-between text-xs text-gray-500">
            <span>Progress: {job.progress}%</span>
            <span class="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {elapsedTime}
            </span>
          </div>
        </div>
        
        <!-- Estimated time remaining -->
        {#if job.progress > 0 && job.progress < 100}
          <div class="mt-2 flex justify-end">
            <span class="text-xs text-gray-500 flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Est. remaining: {estimatedTimeRemaining}
            </span>
          </div>
        {/if}
      </div>
    {/if}
    
    {#if isError}
      <div class="mt-3 bg-red-50 border-l-4 border-red-500 p-3">
        <p class="text-red-700 text-sm">{job.error}</p>
      </div>
    {/if}
    
    <!-- Download files section for completed jobs -->
    {#if job.status === 'completed'}
      <div class="mt-3 space-y-3">
        <!-- Speed control section - Only show for adjusting speed, not after download -->
        {#if showSpeedControl}
          <div class="pb-2 border-b border-gray-200 mt-4">
            <p class="text-sm font-medium text-gray-700">Audio Speed Control</p>
          </div>
          
          {#if speedAdjustmentError}
            <div class="mt-2 mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p class="text-sm text-red-700">{speedAdjustmentError}</p>
            </div>
          {/if}
          
          <div class="mt-2">
            <SpeedControlSlider 
              bind:value={speedFactor}
              on:change={handleSpeedChange}
              disabled={isAdjustingSpeed}
            />
            
            {#if isAdjustingSpeed}
              <div class="mt-3 flex items-center justify-center">
                <div class="flex items-center bg-purple-50 text-purple-700 px-3 py-2 rounded-md text-sm">
                  <svg class="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  Adjusting speed to {Math.round(speedFactor * 100)}%...
                </div>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {/if}
    
    <div class="mt-4 flex flex-wrap gap-2">
      {#if needsTranscriptionReview}
        <div class="w-full p-4 bg-yellow-50 border border-yellow-200 rounded-lg mb-3">
          <div class="flex items-start">
            <div class="flex-shrink-0 mt-0.5">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
            <div class="ml-3">
              <h3 class="text-sm font-medium text-yellow-800">Transcription Ready for Review</h3>
              <div class="mt-1 text-sm text-yellow-700">
                <p>Please review and edit the transcription before generating the voiceover.</p>
              </div>
              <div class="mt-3 flex gap-2">
                <button 
                  class="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white text-sm font-medium rounded-md flex items-center"
                  on:click={handleEditTranscription}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Review & Edit Transcription
                </button>
                
                <button 
                  class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-medium rounded-md flex items-center"
                  on:click={handleConfirmTranscription}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                  Confirm & Continue
                </button>
              </div>
            </div>
          </div>
        </div>
      {/if}
      
      {#if isCompleted}
        <!-- Only show download buttons when URLs are ready -->
        {#if videoUrl}
          <a 
            href={videoUrl} 
            class="px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-md flex items-center"
            download
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download Video
          </a>
        {/if}
        
        {#if audioUrl}
          <a 
            href={audioUrl} 
            class="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-md flex items-center"
            download
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
            Download Audio
          </a>
        {/if}
        
        {#if srtUrl}
          <a 
            href={srtUrl}
            class="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-md flex items-center"
            download
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download Subtitles
          </a>
        {/if}
      {/if}
    </div>
  </div>
</div> 