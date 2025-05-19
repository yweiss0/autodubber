# AutoDubber

AutoDubber is a web application that simplifies the process of replacing the original audio of a video with a new voiceover generated using ElevenLabs Text-to-Speech (TTS).

## Features

- Upload videos to be processed
- Automatic transcription with Whisper AI
- Edit and adjust transcriptions before generating voiceovers
- Select from various ElevenLabs voice options
- Generate high-quality TTS voiceovers
- Download the finished video with new voiceover
- Download audio-only files and subtitles (SRT)
- Real-time job status updates

## Project Structure

The project is split into two main components:

- **Frontend**: Built with Svelte and TailwindCSS
- **Backend**: Built with Python FastAPI

### Prerequisites

- Python 3.8+ (for backend)
- Node.js 16+ (for frontend)
- ffmpeg (for audio/video processing)

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows:
     ```
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

5. Start the backend server:
   ```
   python run.py
   ```
   This will start the FastAPI server at http://localhost:8000

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install the required packages:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run dev
   ```
   This will start the Svelte development server at http://localhost:5173

## Using the Application

1. Open your browser and go to http://localhost:5173
2. Enter your ElevenLabs API key
3. Select a voice from the available options
4. Upload a video file
5. Wait for the transcription to complete
6. Edit the transcription if needed
7. Wait for the voiceover generation and video processing to complete
8. Download your finished video, audio file, or subtitles

## API Endpoints

The backend provides the following API endpoints:

- `POST /upload-video` - Upload a video for processing
- `GET /jobs` - Get all jobs
- `GET /jobs/{job_id}` - Get details for a specific job
- `POST /jobs/{job_id}/update-transcription` - Update the transcription for a job
- `GET /voices` - Get available ElevenLabs voices
- `WebSocket /ws/{job_id}` - Real-time updates for a job

## Technologies Used

- **Frontend**:
  - Svelte/SvelteKit
  - TailwindCSS
  - WebSockets (for real-time updates)

- **Backend**:
  - Python FastAPI
  - OpenAI Whisper (for transcription)
  - ElevenLabs API (for TTS)
  - MoviePy/ffmpeg (for video processing)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [ElevenLabs](https://elevenlabs.io/) for their advanced TTS technology
- [OpenAI Whisper](https://github.com/openai/whisper) for the speech recognition system
- [MoviePy](https://zulko.github.io/moviepy/) for video processing capabilities 