<script>
  import { createEventDispatcher } from 'svelte';
  
  // Props
  export let value = 1.0; // Default to normal speed
  export let min = 0.7;   // 70% speed (slower) - per ElevenLabs docs
  export let max = 1.2;   // 120% speed (faster) - per ElevenLabs docs
  export let step = 0.05; // Step increments
  export let disabled = false;
  
  // For tracking original value
  let originalValue = value;
  let changing = false;
  
  // Dispatch events to parent
  const dispatch = createEventDispatcher();
  
  // Format speed as percentage
  function formatSpeed(speed) {
    return `${Math.round(speed * 100)}%`;
  }
  
  // Handle change
  function handleChange() {
    dispatch('change', { value });
  }
  
  // Handle input (while dragging)
  function handleInput() {
    changing = true;
    dispatch('input', { value });
  }
  
  // Handle blur
  function handleBlur() {
    changing = false;
    
    // Only dispatch if value changed
    if (originalValue !== value) {
      originalValue = value;
      dispatch('change', { value });
    }
  }
  
  // Human-readable speed label
  $: speedLabel = (() => {
    if (value === 1.0) return 'Normal Speed';
    if (value < 1.0) return 'Slower';
    return 'Faster';
  })();
  
  // Determine position for the position indicator text and custom tick marks
  $: {
    // Calculate normalized position for normal speed (1.0)
    const normalizedNormal = (1.0 - min) / (max - min);
  }
</script>

<div class="speed-control py-3">
  <div class="mb-2 flex items-center justify-between">
    <span class="text-sm font-medium text-gray-700">Audio Speed</span>
    <span class="px-2 py-1 text-xs font-medium rounded-full {
      value < 1.0 ? 'bg-blue-100 text-blue-800' : 
      value > 1.0 ? 'bg-yellow-100 text-yellow-800' : 
      'bg-green-100 text-green-800'
    }">{formatSpeed(value)}</span>
  </div>
  
  <div class="relative">
    <!-- Track with custom markings -->
    <div class="h-1 bg-gray-200 rounded-full relative">
      <!-- Normal speed indicator -->
      <div class="absolute h-2 w-0.5 bg-green-600 top-1/2 -translate-y-1/2" style="left: {(1.0 - min) / (max - min) * 100}%"></div>
    </div>
    
    <!-- Labels -->
    <div class="flex justify-between text-xs text-gray-600 mt-1">
      <span>Slower (70%)</span>
      <span class="text-green-600 font-medium">Normal (100%)</span>
      <span>Faster (120%)</span>
    </div>
    
    <!-- Slider -->
    <input 
      type="range"
      class="absolute inset-0 w-full h-4 appearance-none cursor-pointer bg-transparent focus:outline-none disabled:cursor-not-allowed"
      {min}
      {max}
      {step}
      bind:value
      on:change={handleChange}
      on:input={handleInput}
      on:blur={handleBlur}
      {disabled}
    />
  </div>
  
  {#if changing}
    <div class="mt-2 text-xs text-gray-600 text-center">
      {speedLabel} • Release to apply
    </div>
  {/if}
</div>

<style>
  /* Custom styling for the range input */
  input[type="range"] {
    -webkit-appearance: none;
    height: 4px;
    margin-top: -1.5px;
  }
  
  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    height: 16px;
    width: 16px;
    border-radius: 50%;
    background: #4f46e5;
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }
  
  input[type="range"]::-moz-range-thumb {
    height: 16px;
    width: 16px;
    border-radius: 50%;
    background: #4f46e5;
    cursor: pointer;
    border: none;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }
  
  input[type="range"]:focus::-webkit-slider-thumb {
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2);
  }
  
  input[type="range"]:disabled::-webkit-slider-thumb {
    background: #9ca3af;
  }
  
  input[type="range"]:disabled::-moz-range-thumb {
    background: #9ca3af;
  }
</style> 