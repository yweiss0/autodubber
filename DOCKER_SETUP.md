# AutoDubber Docker Setup Guide

## Prerequisites

- Docker Desktop installed on your PC
- ElevenLabs API key (get one from https://elevenlabs.io)

## Quick Start

1. **Clone or download the project** to your PC

2. **Open a terminal/command prompt** in the project root directory (where `docker-compose.yml` is located)

3. **Build and start the containers:**
   ```bash
   docker-compose up --build
   ```

   This command will:
   - Download all necessary dependencies
   - Install FFmpeg and Python packages
   - Build the frontend and backend
   - Start both services

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000

## Usage

1. Open http://localhost:5173 in your browser
2. Enter your ElevenLabs API key
3. Select a voice from the dropdown
4. Upload a video file (MP4, MOV, AVI, or WEBM)
5. Adjust speed if needed (0.7x - 1.2x)
6. Wait for transcription
7. Review and edit the transcription if needed
8. Confirm to generate the voiceover
9. Download your processed video, audio, and subtitle files

## Stopping the Application

To stop the application, press `Ctrl+C` in the terminal where Docker is running, or run:
```bash
docker-compose down
```

## Troubleshooting

### "Cannot connect to backend" or "Loading Jobs..." stuck
- Make sure both containers are running: `docker-compose ps`
- Check the logs: `docker-compose logs`
- Try rebuilding the containers: Run `rebuild.bat` (Windows) or:
  ```bash
  docker-compose down -v
  docker-compose build --no-cache
  docker-compose up
  ```

### Vite pre-transform errors
- This is usually caused by dependency conflicts
- Run `rebuild.bat` to clean and rebuild everything
- If the error persists, delete the frontend's node_modules locally and rebuild

### "File upload fails" or upload stuck
- The application supports files up to 2GB
- Make sure you have enough disk space
- Check backend logs: `docker-compose logs backend`
- Ensure the backend is healthy: `docker-compose ps` should show both containers as "Up"

### "WebSocket connection failed" or job status stuck
- This is normal during container startup
- Wait a few seconds and refresh the page
- Make sure no firewall is blocking WebSocket connections
- If the job seems stuck at a certain percentage, try refreshing the page
- For long-running jobs (larger videos), the WebSocket might disconnect - refreshing will reconnect
- Check backend logs to see if processing is still happening: `docker-compose logs --follow backend`

### Resetting Everything
If you need to start fresh:
```bash
docker-compose down -v
docker-compose up --build
```

## Advanced Options

### Running in Background
To run the containers in the background:
```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f
```

### Rebuilding After Code Changes
Since we mount the source code as volumes, most changes will be reflected automatically.
However, if you change dependencies, rebuild:
```bash
docker-compose build
docker-compose up
```

### Storage
- Uploaded videos are stored in `backend/media/uploads/`
- Processed files are stored in `backend/media/outputs/`
- Temporary files are in `backend/media/temp/`

These directories are mounted as volumes, so files persist between container restarts.

## System Requirements

- **RAM**: At least 4GB recommended (8GB+ for larger videos)
- **Storage**: Enough space for your video files (3x the size of your largest video)
- **CPU**: Multi-core processor recommended for faster processing

## Notes

- The first time you run the containers, it will take longer as Docker downloads all dependencies
- Whisper model will be downloaded on first use (~140MB)
- Processing time depends on video length and your hardware
- The application runs entirely on your local machine - no data is sent to external servers except for the ElevenLabs API calls 