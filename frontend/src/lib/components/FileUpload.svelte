<script>
  import { createEventDispatcher } from 'svelte';
  import { uploadVideo } from '$lib/api';
  import SpeedControlSlider from './SpeedControlSlider.svelte';
  
  // Props
  export let apiKey = '';
  export let voiceId = '';
  
  // State
  let file = null;
  let filename = '';
  let filesize = 0;
  let error = null;
  let uploading = false;
  let uploadProgress = 0;
  let uploadProgressVisible = false;
  let uploadIconAnimating = false;
  let speedFactor = 1.0; // Default speed factor
  let isDragOver = false;
  
  // Events
  const dispatch = createEventDispatcher();
  
  // Handle file selection
  const onFileSelected = (event) => {
    const selectedFile = event?.target?.files?.[0] || file;
    
    if (selectedFile) {
      file = selectedFile;
      filename = file.name;
      filesize = file.size;
      error = null;
      
      // Check file type
      const fileType = file.type.toLowerCase();
      const validTypes = ['video/mp4', 'video/quicktime', 'video/webm', 'video/avi'];
      
      if (!validTypes.includes(fileType)) {
        error = 'Please select a valid video file (MP4, MOV, WEBM, or AVI).';
        file = null;
        return;
      }
      
      // Check file size (100MB limit)
      const maxSize = 100 * 1024 * 1024; // 100MB in bytes
      if (file.size > maxSize) {
        error = 'File is too large. Maximum size is 100MB.';
        file = null;
        return;
      }
    }
  };
  
  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  // Clear selected file
  const clearFile = () => {
    file = null;
    const input = document.getElementById('file-upload');
    if (input) input.value = '';
    error = null;
  };
  
  function simulateUploadProgress() {
    uploadProgress = 0;
    uploadProgressVisible = true;
    uploadIconAnimating = true;
    
    // Simulate progress - this will be replaced by actual upload progress in production
    const interval = setInterval(() => {
      uploadProgress += 5;
      
      if (uploadProgress >= 100) {
        clearInterval(interval);
      }
    }, 100);
    
    return interval;
  }
  
  // Upload the selected file
  const uploadFile = async () => {
    if (!file) return;
    if (!apiKey) {
      error = 'Please enter your ElevenLabs API key.';
      return;
    }
    
    try {
      uploading = true;
      error = null;
      
      // Start progress animation
      const progressInterval = simulateUploadProgress();
      
      // Call the API to upload the file
      const result = await uploadVideo(file, voiceId, apiKey, speedFactor);
      
      // Ensure progress bar reaches 100%
      uploadProgress = 100;
      setTimeout(() => {
        clearInterval(progressInterval);
        
        // Dispatch an event with the job ID
        dispatch('uploaded', { jobId: result.job_id });
        
        // Reset UI after a short delay
        setTimeout(() => {
          file = null;
          uploadProgressVisible = false;
          uploadIconAnimating = false;
          uploading = false;
        }, 1000);
      }, 500);
      
    } catch (err) {
      uploadProgressVisible = false;
      uploadIconAnimating = false;
      error = err.message || 'Failed to upload file. Please try again.';
      uploading = false;
    }
  };
  
  // Handle speed change
  function handleSpeedChange(event) {
    speedFactor = event.detail.value;
  }
  
  // Handle drag and drop events
  function handleDragEnter(e) {
    e.preventDefault();
    e.stopPropagation();
    isDragOver = true;
  }
  
  function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    isDragOver = false;
  }
  
  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    isDragOver = true;
  }
  
  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    isDragOver = false;
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      file = e.dataTransfer.files[0];
      onFileSelected();
    }
  }
</script>

<div class="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
  <h2 class="text-lg font-semibold text-gray-800 mb-3">Upload Video</h2>
  
  <div class="mb-4">
    <label for="file-upload" class="block mb-2 text-sm font-medium text-gray-700">
      Choose a video file or drag and drop it below
    </label>
    
    {#if !file}
      <div class="relative">
        <input 
          id="file-upload" 
          type="file" 
          accept="video/mp4,video/quicktime,video/webm,video/avi"
          on:change={onFileSelected}
          disabled={uploading}
          class="hidden"
        />
        <label 
          for="file-upload" 
          class="flex flex-col justify-center items-center h-40 px-4 border-2 border-dashed rounded-lg transition-colors cursor-pointer {
            isDragOver 
              ? 'border-indigo-400 bg-indigo-50' 
              : 'border-gray-300 hover:bg-gray-50 hover:border-gray-400'
          } {uploading ? 'opacity-50 cursor-not-allowed' : ''}"
          on:dragenter={handleDragEnter}
          on:dragleave={handleDragLeave}
          on:dragover={handleDragOver}
          on:drop={handleDrop}
        >
          <div class="text-center">
            <svg class="mx-auto h-14 w-14 {isDragOver ? 'text-indigo-500' : 'text-gray-400'}" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
            <p class="mt-2 text-sm font-medium {isDragOver ? 'text-indigo-600' : 'text-gray-700'}">
              {isDragOver ? 'Drop video file here' : 'Drag and drop a video file here'}
            </p>
            <p class="mt-1 text-xs {isDragOver ? 'text-indigo-400' : 'text-gray-500'}">- or -</p>
            <p class="mt-2">
              <span class="px-3 py-1.5 text-xs font-medium bg-indigo-100 text-indigo-700 rounded-md hover:bg-indigo-200 transition-colors">
                Browse Files
              </span>
            </p>
            <p class="mt-2 text-xs text-gray-500">MP4, MOV, WEBM, or AVI (Max. 100MB)</p>
          </div>
        </label>
      </div>
    {:else}
      <div class="bg-gray-50 rounded-lg border border-gray-200 p-3">
        <div class="flex justify-between items-center">
          <div class="flex items-center truncate flex-1">
            <svg class="w-8 h-8 text-gray-400 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
            <div class="truncate">
              <p class="text-sm font-medium text-gray-800 truncate">{filename}</p>
              <p class="text-xs text-gray-500">{formatFileSize(filesize)}</p>
            </div>
          </div>
          <button 
            on:click={clearFile} 
            disabled={uploading}
            class="ml-3 text-gray-400 hover:text-gray-700 transition-colors {uploading ? 'opacity-50 cursor-not-allowed' : ''}"
          >
            <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <!-- Speed control slider BEFORE uploading -->
        <div class="mt-4 border-t border-gray-200 pt-4">
          <SpeedControlSlider 
            bind:value={speedFactor}
            on:change={handleSpeedChange}
            disabled={uploading}
          />
          <p class="text-xs text-gray-500 mt-2 italic">
            Speed affects how fast the generated voice will speak. Normal speed is 100%.
          </p>
        </div>
        
        {#if uploadProgressVisible}
          <div class="mt-4 relative pt-1">
            <div class="overflow-hidden h-2 text-xs flex rounded bg-gray-200">
              <div class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500 transition-all" style="width: {uploadProgress}%"></div>
            </div>
            <div class="flex mt-1 text-xs justify-end">
              <span class="text-gray-600">{uploadProgress}%</span>
            </div>
          </div>
        {/if}
      </div>
    {/if}
    
    {#if error}
      <p class="mt-2 text-sm text-red-600">{error}</p>
    {/if}
  </div>
  
  <div class="flex justify-end">
    <button 
      on:click={uploadFile}
      disabled={!file || !apiKey || uploading}
      class="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
    >
      {#if uploadIconAnimating}
        <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
      {:else}
        <svg class="-ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      {/if}
      {uploading ? 'Uploading...' : 'Start Processing'}
    </button>
  </div>
</div> 