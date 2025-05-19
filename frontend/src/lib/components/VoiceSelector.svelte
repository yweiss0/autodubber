<script>
  import { onMount } from 'svelte';
  import { fetchVoices } from '$lib/api';
  
  export let apiKey = '';
  export let selectedVoiceId = 'uYkKk3J4lEp7IHQ8CLBi'; // Default Justin voice
  
  let voices = [];
  let loading = false;
  let error = null;
  
  // Load voices when the API key is provided
  $: if (apiKey) {
    console.log(`API key changed in VoiceSelector, loading voices with key length: ${apiKey.length}`);
    loadVoices();
  }
  
  async function loadVoices() {
    if (!apiKey) {
      console.log("No API key provided, cannot load voices");
      return;
    }
    
    try {
      loading = true;
      error = null;
      console.log("Starting to fetch voices...");
      voices = await fetchVoices(apiKey);
      console.log(`Successfully loaded ${voices.length} voices`);
    } catch (err) {
      console.error("Error loading voices:", err);
      error = err.message || 'Failed to load voices. Please check your API key.';
      voices = [];
    } finally {
      loading = false;
    }
  }
  
  // Handle voice selection change
  function handleVoiceChange(event) {
    selectedVoiceId = event.target.value;
  }
  
  // Play voice sample
  function playVoiceSample(previewUrl) {
    if (!previewUrl) return;
    
    const audio = new Audio(previewUrl);
    audio.play();
  }
</script>

<div class="bg-white p-6 rounded-lg shadow-md mb-4">
  <h2 class="text-xl font-semibold text-gray-800 mb-4">Select Voice</h2>
  
  {#if loading}
    <div class="flex items-center justify-center p-4">
      <svg class="animate-spin h-5 w-5 text-blue-600 mr-3" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      <span class="text-gray-600">Loading voices...</span>
    </div>
  {:else if error}
    <div class="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
      <p class="text-red-700">{error}</p>
    </div>
  {:else if voices.length > 0}
    <div class="mb-4">
      <label for="voiceSelect" class="block text-sm font-medium text-gray-700 mb-1">Voice</label>
      <select
        id="voiceSelect"
        class="w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        value={selectedVoiceId}
        on:change={handleVoiceChange}
      >
        {#each voices as voice}
          <option value={voice.voice_id}>{voice.name}</option>
        {/each}
      </select>
    </div>
    
    {#if selectedVoiceId}
      {#each voices as voice}
        {#if voice.voice_id === selectedVoiceId}
          <div class="bg-gray-50 p-3 rounded-md">
            <div class="flex justify-between items-center mb-2">
              <span class="font-medium text-gray-800">{voice.name}</span>
              {#if voice.preview_url}
                <button
                  class="flex items-center text-sm text-blue-600 hover:text-blue-800"
                  on:click={() => playVoiceSample(voice.preview_url)}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Play Sample
                </button>
              {/if}
            </div>
            {#if voice.description}
              <p class="text-sm text-gray-600">{voice.description}</p>
            {/if}
          </div>
        {/if}
      {/each}
    {/if}
  {:else if apiKey}
    <p class="text-gray-600">No voices found. Please check your API key.</p>
  {:else}
    <p class="text-gray-600">Enter your ElevenLabs API key to load available voices.</p>
  {/if}
</div> 