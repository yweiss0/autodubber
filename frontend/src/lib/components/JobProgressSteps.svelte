<script>
  // Props: job object containing status and other details
  export let job = {};
  
  // Debug logging
  $: console.log(`JobProgressSteps received job:`, {
    jobId: job?.job_id,
    status: job?.status,
    progress: job?.progress,
    current_activity: job?.current_activity
  });

  // Define the processing steps in order
  const steps = [
    { id: "extracting_audio", label: "Extract Audio" },
    { id: "transcribing", label: "Transcribe Audio" },
    { id: "generating_tts", label: "Generate Speech" },
    { id: "creating_voiceover", label: "Assemble Audio" },
    { id: "creating_video", label: "Create Video" }
  ];

  // Function to determine step status based on job status
  function getStepStatus(stepId) {
    // Status mapping from backend to our step model
    const statusMapping = {
      "uploaded": -1, // Not started any step yet
      "extracting_audio": 0,
      "transcribing": 1, 
      "transcription_complete": 1, // Still in transcription phase
      "transcription_confirmed": 2, // Moving to TTS generation
      "generating_tts": 2,
      "creating_voiceover": 3,
      "creating_video": 4,
      "adjusting_speed": 3, // Consider speed adjustment part of audio assembly
      "creating_adjusted_video": 4,
      "completed": 5, // All steps completed
      "error": -2 // Error state
    };
    
    const currentStepIndex = statusMapping[job.status] || -1;
    
    // Find the index of this step in our defined steps
    const thisStepIndex = steps.findIndex(step => step.id === stepId);
    
    // Error state - mark all steps as error
    if (currentStepIndex === -2) return "error";
    
    // Special case handling for some statuses that don't map directly to step ids
    if (job.status === "generating_tts" && stepId === "generating_tts") return "active";
    if (job.status === "transcription_confirmed" && stepId === "generating_tts") return "active";
    
    // Step completed
    if (currentStepIndex > thisStepIndex) return "completed";
    
    // Current step
    if (currentStepIndex === thisStepIndex) return "active";
    
    // Not reached yet
    return "pending";
  }
</script>

<!-- Stepper design based on the images provided -->
<div class="py-4">
  <div class="relative flex items-center justify-between mb-8">
    <!-- Progress line -->
    <!-- <div class="absolute h-1 bg-gray-200 left-0 right-0 top-1/2 transform -translate-y-1/2 z-0"></div> -->
    
    {#each steps as step, index}
      {@const status = getStepStatus(step.id)}
      <div class="relative z-10 flex flex-col items-center">
        <!-- Circle with number or check icon -->
        {#if status === 'completed'}
          <div class="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              
            </svg>
            
          </div>
        {:else if status === 'active'}
          <div class="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white">
            <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>

            </svg>
            
          </div>
        {:else}
          <div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
            {index + 1}
          </div>
        {/if}
        
        <!-- Label -->
        <div class="text-xs mt-2 text-center max-w-[60px] {status === 'completed' || status === 'active' ? 'font-medium text-gray-800' : 'text-gray-500'}">
          {step.label}
        </div>
      </div>
    {/each}
  </div>
  
  {#if job.current_activity}
    <div class="text-xs text-gray-500 text-center mt-2 border-t pt-2">{job.current_activity}</div>
  {/if}
</div> 