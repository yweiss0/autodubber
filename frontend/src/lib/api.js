// API base URL - adjust based on your deployment
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Fetch available voices from ElevenLabs API
 * @param {string} apiKey - The ElevenLabs API key
 * @returns {Promise<Array>} - List of available voices
 */
export const fetchVoices = async (apiKey) => {
  console.log(`Fetching voices with API key (${apiKey.length} characters)`);
  
  const response = await fetch(`${API_BASE_URL}/voices`, {
    headers: {
      'xi-api-key': apiKey
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    console.error("Error fetching voices:", error);
    throw new Error(error.detail || 'Failed to fetch voices');
  }
  
  return response.json();
};

/**
 * Upload a video file for processing
 * @param {File} file - The video file to upload
 * @param {string} voiceId - The ElevenLabs voice ID to use
 * @param {string} apiKey - The ElevenLabs API key
 * @param {number} speedFactor - The speed factor (0.7-1.2, 1.0 is normal)
 * @returns {Promise<Object>} - Job details
 */
export const uploadVideo = async (file, voiceId, apiKey, speedFactor = 1.0) => {
  console.log(`Uploading video with API key (${apiKey.length} characters), voice ID: ${voiceId}, speed: ${speedFactor}`);
  
  const formData = new FormData();
  formData.append('file', file);
  formData.append('voice_id', voiceId);
  formData.append('speed_factor', speedFactor);
  // Keeping for backward compatibility but prefer header
  formData.append('elevenlabs_api_key', apiKey);
  
  const response = await fetch(`${API_BASE_URL}/upload-video`, {
    method: 'POST',
    headers: {
      'xi-api-key': apiKey
    },
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json();
    console.error("Error uploading video:", error);
    throw new Error(error.detail || 'Failed to upload video');
  }
  
  return response.json();
};

/**
 * Fetch all jobs
 * @returns {Promise<Object>} - All jobs
 */
export const fetchJobs = async () => {
  const response = await fetch(`${API_BASE_URL}/jobs`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch jobs');
  }
  
  return response.json();
};

/**
 * Fetch a specific job
 * @param {string} jobId - The job ID
 * @returns {Promise<Object>} - Job details
 */
export const fetchJob = async (jobId) => {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch job');
  }
  
  return response.json();
};

/**
 * Update the transcription for a job
 * @param {string} jobId - The job ID
 * @param {Array} transcription - The updated transcription segments
 * @returns {Promise<Object>} - Response
 */
export const updateTranscription = async (jobId, transcription) => {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/update-transcription`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(transcription),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update transcription');
  }
  
  return response.json();
};

/**
 * Adjust the speed of audio for a job
 * @param {string} jobId - The job ID
 * @param {number} speedFactor - The speed factor (1.0 is normal speed)
 * @returns {Promise<Object>} - Job status
 */
export const adjustAudioSpeed = async (jobId, speedFactor) => {
  const formData = new FormData();
  formData.append('speed_factor', speedFactor);
  
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/adjust-speed`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json();
    console.error("Error adjusting audio speed:", error);
    throw new Error(error.detail || 'Failed to adjust audio speed');
  }
  
  return response.json();
};

/**
 * Get the full system path for a file
 * @param {string} fileType - The type of file (video, audio, srt)
 * @param {string} jobId - The job ID
 * @returns {Promise<string>} - The full system path
 */
export const getFilePath = async (fileType, jobId) => {
  const response = await fetch(`${API_BASE_URL}/file-path/${fileType}/${jobId}`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to get ${fileType} file path`);
  }
  
  const data = await response.json();
  return data.path;
};

/**
 * Create a WebSocket connection for real-time job updates
 * @param {string} jobId - The job ID
 * @param {Function} onMessage - Callback for message events
 * @param {Function} onClose - Callback for close events
 * @returns {WebSocket} - WebSocket instance
 */
export const createJobWebSocket = (jobId, onMessage, onClose) => {
  // WebSocket URL based on current protocol (ws: or wss:)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // Extract the hostname and port from the API_BASE_URL or use the current window location
  let wsUrl;
  
  if (API_BASE_URL.startsWith('http')) {
    // Extract hostname and port from API_BASE_URL
    const url = new URL(API_BASE_URL);
    wsUrl = `${protocol}//${url.host}/ws/${jobId}`;
  } else {
    // Use window location
    wsUrl = `${protocol}//${window.location.host}/ws/${jobId}`;
  }
  
  console.log(`Creating WebSocket connection to: ${wsUrl}`);
  const socket = new WebSocket(wsUrl);
  
  // Variables for automatic reconnection
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 10; // Increased from 5 to 10
  const reconnectInterval = 2000; // Reduced from 3000 to 2000 ms for faster reconnection
  let reconnectTimeout = null;
  let pingInterval = null;
  let lastMessageTime = Date.now();
  
  // Function to handle reconnection
  const reconnect = () => {
    if (reconnectAttempts >= maxReconnectAttempts) {
      console.error(`Maximum reconnect attempts (${maxReconnectAttempts}) reached for job ${jobId}`);
      if (onClose) onClose(); // Notify caller about permanent disconnect
      return;
    }
    
    reconnectAttempts++;
    console.log(`Attempting to reconnect WebSocket for job ${jobId}, attempt ${reconnectAttempts}/${maxReconnectAttempts}`);
    
    // Clear any existing timeout
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
    }
    
    // Set timeout to reconnect
    reconnectTimeout = setTimeout(() => {
      console.log(`Reconnecting WebSocket for job ${jobId}...`);
      // Return value from recursive call
      const newSocket = createJobWebSocket(jobId, onMessage, onClose);
      
      // Transfer any properties or event handlers if needed
      // This is a way to "replace" the current socket with the new one
      if (newSocket.readyState === WebSocket.OPEN) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onclose = null;
        socket.onerror = null;
        try {
          socket.close();
        } catch (e) {
          console.warn("Error closing old socket:", e);
        }
      }
    }, reconnectInterval * Math.min(reconnectAttempts, 3)); // Gradually increase reconnect time
  };
  
  // Function to monitor connection health
  const startConnectionHealthCheck = () => {
    // Clear any existing interval
    if (pingInterval) {
      clearInterval(pingInterval);
    }
    
    // Set interval to check connection health
    pingInterval = setInterval(() => {
      const now = Date.now();
      const elapsed = now - lastMessageTime;
      
      // If it's been more than 15 seconds since last message, try to reconnect
      if (elapsed > 15000 && socket.readyState === WebSocket.OPEN) {
        console.warn(`No messages received for ${elapsed/1000}s, sending ping to check connection`);
        try {
          // Try to send a ping to verify connection
          socket.send(JSON.stringify({ type: 'ping', timestamp: now }));
        } catch (e) {
          console.error("Error sending ping, connection may be dead:", e);
          socket.close();
        }
      }
      
      // If it's been more than 30 seconds with no activity, force reconnect
      if (elapsed > 30000) {
        console.error(`No messages received for ${elapsed/1000}s, forcing reconnect`);
        socket.close();
      }
    }, 5000); // Check every 5 seconds
  };
  
  socket.onopen = () => {
    console.log(`WebSocket connection opened for job: ${jobId}`);
    // Reset reconnect attempts on successful connection
    reconnectAttempts = 0;
    lastMessageTime = Date.now();
    
    // Start connection health monitoring
    startConnectionHealthCheck();
    
    // Send an initial message to request current state
    try {
      socket.send(JSON.stringify({ 
        action: 'get_status',
        job_id: jobId,
        timestamp: Date.now()
      }));
    } catch (e) {
      console.warn("Error sending initial status request:", e);
    }
  };
  
  socket.onmessage = (event) => {
    // Update last message time
    lastMessageTime = Date.now();
    
    try {
      const data = JSON.parse(event.data);
      
      // Handle ping messages from server
      if (data.type === 'ping') {
        console.debug(`Received ping from server for job ${jobId}:`, data);
        
        // If the ping contains status info, forward it to the client
        if (data.status && data.job_id) {
          // Create a simplified status update from the ping
          const statusUpdate = {
            job_id: data.job_id,
            status: data.status,
            progress: data.progress || 0,
            current_activity: data.current_activity || '',
            timestamp: data.timestamp || Date.now()
          };
          
          // Forward status info to handler
          console.log(`Processing status update from ping for job ${jobId}:`, statusUpdate);
          onMessage(statusUpdate);
        }
        
        return;
      }
      
      console.log(`WebSocket message received for job ${jobId}:`, data);
      
      // Ensure we have at least the minimal fields needed
      if (!data.job_id) data.job_id = jobId;
      if (data.progress === undefined) data.progress = 0;
      
      // Call the message handler
      onMessage(data);
    } catch (e) {
      console.error("Error processing WebSocket message:", e, event.data);
    }
  };
  
  socket.onclose = (event) => {
    console.log(`WebSocket connection closed for job: ${jobId}`, event);
    
    // Clear intervals
    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }
    
    // If the close wasn't clean and we still have reconnect attempts left, try to reconnect
    if (!event.wasClean && reconnectAttempts < maxReconnectAttempts) {
      console.log(`Attempting to reconnect after close for job ${jobId}`);
      reconnect();
    } else {
      // If we're out of reconnect attempts or it was a clean close, notify caller
      if (onClose) onClose();
    }
  };
  
  socket.onerror = (error) => {
    console.error(`WebSocket error for job: ${jobId}`, error);
    // No need to close here, the onclose handler will be called automatically
  };
  
  return socket;
}; 