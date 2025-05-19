<script>
  import { createEventDispatcher } from 'svelte';
  import { updateTranscription } from '$lib/api.js';
  import SpeedControlSlider from './SpeedControlSlider.svelte';
  
  // Props
  export let jobId;
  export let segments = [];
  export let initialSpeedFactor = 1.0; // Accept initial speed factor from parent
  
  // Local state
  let editedSegments = JSON.parse(JSON.stringify(segments));
  let error = null;
  let saving = false;
  let speedFactor = initialSpeedFactor; // Initialize with the passed value
  
  // Events
  const dispatch = createEventDispatcher();
  
  // Handle submit
  async function handleSubmit() {
    try {
      error = null;
      saving = true;
      
      // Create a version that preserves the original timing information
      const updatedSegments = editedSegments.map(segment => ({
        start: segment.start,  // Preserve original start time
        end: segment.end,      // Preserve original end time
        text: segment.text     // Use the edited text
      }));
      
      // Update transcription segments
      await updateTranscription(jobId, updatedSegments);
      
      // Update the speed factor through a WebSocket message
      const socket = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/${jobId}`);
      
      // Wait for socket to open before sending
      socket.onopen = function() {
        socket.send(JSON.stringify({
          action: 'update_transcription',
          transcription: updatedSegments,
          speed_factor: speedFactor // Send the speed factor to be applied
        }));
        socket.close();
      };
      
      // Dispatch event to parent
      dispatch('transcriptionUpdated');
    } catch (err) {
      error = err.message || 'Failed to update transcription.';
    } finally {
      saving = false;
    }
  }
  
  // Handle cancel
  function handleCancel() {
    dispatch('cancel');
  }
  
  // Handle input changes for a segment
  function handleSegmentChange(index, text) {
    editedSegments[index].text = text;
  }
  
  // Handle speed slider change
  function handleSpeedChange(event) {
    speedFactor = event.detail.value;
  }
</script>

<div class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
  <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
    <div class="p-6 border-b border-gray-200">
      <h2 class="text-xl font-semibold text-gray-800">Edit Transcription</h2>
      <p class="text-gray-600 mt-1">Modify the text for each segment before generating the voiceover.</p>
    </div>
    
    <div class="p-6 overflow-y-auto flex-grow">
      {#if error}
        <div class="mb-4 p-4 bg-red-50 border-l-4 border-red-500 text-red-700">
          {error}
        </div>
      {/if}
      
      <div class="space-y-4">
        {#each editedSegments as segment, index}
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex justify-between text-sm text-gray-500 mb-2">
              <span>Segment {index + 1}</span>
              <span>
                {new Date(segment.start * 1000).toISOString().substr(11, 8)} - 
                {new Date(segment.end * 1000).toISOString().substr(11, 8)}
              </span>
            </div>
            <textarea 
              bind:value={segment.text} 
              on:input={() => handleSegmentChange(index, segment.text)}
              rows="2"
              class="w-full p-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
            ></textarea>
          </div>
        {/each}
      </div>
      
      <!-- Speed control section -->
      <div class="mt-8 border-t border-gray-200 pt-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Audio Speed Setting</h3>
        <p class="text-sm text-gray-600 mb-4">
          Adjust the playback speed for the AI voiceover. This affects how quickly the generated voice will speak.
        </p>
        
        <div class="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <SpeedControlSlider 
            bind:value={speedFactor}
            on:change={handleSpeedChange}
          />
          <p class="text-xs text-gray-500 mt-3 italic">
            Normal speed is 100%. Slower speeds (70%-90%) may sound more natural for some voices, 
            while faster speeds (110%-120%) can make the speech more concise.
          </p>
        </div>
      </div>
    </div>
    
    <div class="p-6 border-t border-gray-200 bg-gray-50 flex justify-end space-x-4">
      <button 
        on:click={handleCancel}
        class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
      >
        Cancel
      </button>
      <button 
        on:click={handleSubmit}
        disabled={saving}
        class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
      >
        {#if saving}
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          Saving...
        {:else}
          Confirm & Generate Voiceover
        {/if}
      </button>
    </div>
  </div>
</div> 