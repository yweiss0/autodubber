<script>
  import { onMount } from 'svelte';
  
  export let apiKey = '';
  
  let showKey = false;
  let inputType = 'password';
  let isSaved = false;
  
  // Toggle password visibility
  function toggleVisibility() {
    showKey = !showKey;
    inputType = showKey ? 'text' : 'password';
  }
  
  // Save API key to localStorage
  function saveApiKey() {
    if (apiKey) {
      localStorage.setItem('elevenlabs_api_key', apiKey);
      console.log(`API key saved (${apiKey.length} characters)`);
      isSaved = true;
      
      // Auto-hide saved message after 3 seconds
      setTimeout(() => {
        isSaved = false;
      }, 3000);
    }
  }
  
  // Load API key from localStorage on mount
  onMount(() => {
    const savedKey = localStorage.getItem('elevenlabs_api_key');
    if (savedKey) {
      console.log(`Loaded saved API key (${savedKey.length} characters)`);
      apiKey = savedKey;
    }
  });
</script>

<div class="bg-white p-6 rounded-lg shadow-md mb-4">
  <h2 class="text-xl font-semibold text-gray-800 mb-4">ElevenLabs API Key</h2>
  
  <div class="mb-4">
    <label for="apiKeyInput" class="block text-sm font-medium text-gray-700 mb-1">
      API Key
    </label>
    <div class="relative rounded-md shadow-sm">
      <input
        id="apiKeyInput"
        type={inputType}
        bind:value={apiKey}
        placeholder="Enter your ElevenLabs API key"
        class="block w-full pr-10 py-2 px-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
      />
      <button
        type="button"
        class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-gray-700"
        on:click={toggleVisibility}
      >
        {#if showKey}
          <!-- Hide icon -->
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
          </svg>
        {:else}
          <!-- Show icon -->
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        {/if}
      </button>
    </div>
    <p class="mt-1 text-xs text-gray-500">
      Your API key is only sent directly to the ElevenLabs API and is never stored on our servers.
    </p>
  </div>
  
  <div class="flex items-center">
    <button
      class="py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-md transition-colors"
      disabled={!apiKey}
      on:click={saveApiKey}
    >
      Save API Key
    </button>
    
    {#if isSaved}
      <span class="ml-3 text-sm text-green-600">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        API key saved locally
      </span>
    {/if}
  </div>
</div> 