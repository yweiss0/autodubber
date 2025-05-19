from fastapi import (
    FastAPI,
    File,
    UploadFile,
    BackgroundTasks,
    HTTPException,
    Form,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import shutil
import uuid
import asyncio
import json
import logging
from datetime import datetime
import re
import sys
from io import StringIO
import time
import random

# Import the video_voiceover functionality
from video_voiceover import (
    extract_audio_from_video,
    transcribe_audio,
    generate_tts_for_segments,
    create_composite_voiceover,
    create_final_video,
    save_srt_file,
    list_available_voices,
    VOICE_SETTINGS,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("autodubber")

# Create FastAPI app
app = FastAPI(title="AutoDubber API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
UPLOAD_DIR = os.path.join(os.getcwd(), "media", "uploads")
OUTPUT_DIR = os.path.join(os.getcwd(), "media", "outputs")
TEMP_DIR = os.path.join(os.getcwd(), "media", "temp")

for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)

# Mount the media directory for file downloads
app.mount("/media", StaticFiles(directory="media"), name="media")


# Models
class Job(BaseModel):
    job_id: str
    filename: str
    status: str
    progress: float = 0
    created_at: str
    finished_at: Optional[str] = None
    error: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    srt_path: Optional[str] = None
    transcription: Optional[List[Dict[str, Any]]] = None
    voice_id: Optional[str] = None
    speed_factor: float = 1.0
    current_activity: Optional[str] = None  # Added field for detailed status message


# In-memory job storage (replace with database in production)
jobs = {}

# WebSocket connections for real-time updates
active_connections: Dict[str, List[WebSocket]] = {}

# Status messages for different job states
statusMessages = {
    "uploaded": "File uploaded, waiting to process",
    "extracting_audio": "Extracting audio from video",
    "transcribing": "Transcribing audio with Whisper AI",
    "transcription_complete": "Transcription ready for review",
    "transcription_confirmed": "Generating AI voiceover",
    "generating_tts": "Generating AI voiceover with ElevenLabs",
    "creating_voiceover": "Assembling audio segments",
    "creating_video": "Creating final video with voiceover",
    "adjusting_speed": "Adjusting audio speed",
    "creating_adjusted_video": "Creating video with adjusted audio",
    "completed": "Processing complete",
    "error": "Error occurred during processing",
}


# Helper functions
async def broadcast_job_update(job_id: str, data: dict):
    """Send job updates to all connected WebSocket clients for this job."""
    if job_id in active_connections:
        connection_count = len(active_connections[job_id])
        logger.info(
            f"Broadcasting update for job {job_id} to {connection_count} client(s): status={data.get('status')}, progress={data.get('progress')}, activity={data.get('current_activity')}"
        )
        for connection in active_connections[job_id]:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
    else:
        logger.warning(
            f"No active connections for job {job_id}, update not broadcasted"
        )


# Create a separate function to run the broadcast in the background
async def run_broadcast(job_id: str, data: dict):
    """Run broadcast as a separate task to ensure it completes."""
    try:
        await broadcast_job_update(job_id, data)
    except Exception as e:
        logger.error(f"Error in background broadcast task: {e}")


def update_job_status(
    job_id: str,
    status: str,
    progress: float = None,
    error: str = None,
    finished_at: str = None,
    current_activity: str = None,
    **kwargs,
):
    """Update job status and broadcast the update to all connected clients."""
    if job_id in jobs:
        prev_status = jobs[job_id].get("status")
        prev_progress = jobs[job_id].get("progress", 0)
        prev_activity = jobs[job_id].get("current_activity", "")

        # Check if this is a meaningful update
        has_status_change = status != prev_status
        has_progress_change = (
            progress is not None and abs(progress - prev_progress) >= 1
        )
        has_activity_change = (
            current_activity is not None and current_activity != prev_activity
        )

        if has_status_change or has_progress_change or has_activity_change:
            logger.info(
                f"Updating job {job_id} status: {prev_status} -> {status}, progress: {prev_progress} -> {progress}, activity: {prev_activity} -> {current_activity}"
            )

            jobs[job_id]["status"] = status
            if progress is not None:
                jobs[job_id]["progress"] = progress
            if error:
                jobs[job_id]["error"] = error
            if finished_at:
                jobs[job_id]["finished_at"] = finished_at
            if current_activity:
                jobs[job_id]["current_activity"] = current_activity

            # Update any additional fields
            for key, value in kwargs.items():
                jobs[job_id][key] = value

            # Create a background task to broadcast the update
            # This ensures the update is sent even during long-running operations
            asyncio.create_task(run_broadcast(job_id, jobs[job_id]))

            # Log the task creation
            logger.info(f"Created background task to broadcast update for job {job_id}")

        return jobs[job_id]
    return None


# Redirect stdout to capture progress messages
class ProgressCapture:
    def __init__(self, job_id):
        self.job_id = job_id
        self.old_stdout = sys.stdout
        self.captured = StringIO()
        self.last_update_time = time.time()
        self.update_interval = 0.3  # Send updates more frequently (was 0.5s)
        self.batched_messages = []
        self.last_progress = 0  # Track the last reported progress value

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.old_stdout
        # Flush any remaining messages
        self._send_batched_updates()

    def write(self, text):
        self.old_stdout.write(text)
        self.captured.write(text)

        # Check for progress update patterns
        if "PROGRESS_UPDATE:" in text:
            # Extract the message after the marker
            message = text.split("PROGRESS_UPDATE:", 1)[1].strip()
            # Batch the message for update
            self.batched_messages.append(message)
            self._maybe_send_update()

        elif "ERROR:" in text:
            # Extract error message
            error_msg = text.split("ERROR:", 1)[1].strip()
            # Update job with error information but don't change status
            if self.job_id in jobs:
                update_job_status(
                    self.job_id, jobs[self.job_id]["status"], error=error_msg
                )

    def _maybe_send_update(self):
        """Send updates at most every update_interval seconds"""
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self._send_batched_updates()

    def _send_batched_updates(self):
        """Send all batched messages as a single update"""
        if not self.batched_messages or self.job_id not in jobs:
            return

        # Use the most recent message as the current activity
        most_recent = self.batched_messages[-1]

        # More fine-grained progress indicators - expanded for better granularity
        progress_indicators = {
            # Audio extraction phase - 0-15%
            "audio extraction": 10,
            "extracting audio": 5,
            "extracted audio": 15,
            # Transcription phase - 15-40%
            "loading whisper": 18,
            "whisper model loaded": 20,
            "beginning transcription": 25,
            "transcribing": 30,
            "transcription completed": 40,
            # TTS generation phase - 40-80%
            "generating tts": 45,
            "tts generating segment": 55,
            "voiceover assembly": 70,
            "voiceover assembly completed": 80,
            # Final video creation - 80-100%
            "creating final video": 85,
            "encoding final video": 95,
            "completed successfully": 100,
        }

        # Default to incrementing progress slightly if we can't match a specific indicator
        progress = None
        current_status = jobs[self.job_id]["status"]

        # Determine progress
        for indicator, value in progress_indicators.items():
            if indicator.lower() in most_recent.lower():
                progress = value
                break

        # If no specific progress found, increment slightly based on status
        if progress is None:
            status_progress_map = {
                "extracting_audio": 8,
                "transcribing": 25,
                "transcription_complete": 40,
                "transcription_confirmed": 45,
                "generating_tts": 60,
                "creating_voiceover": 75,
                "creating_video": 90,
                "adjusting_speed": 85,
                "creating_adjusted_video": 95,
            }

            # If we're in a known status, use its default progress value
            # but only if it's higher than the last known progress
            if current_status in status_progress_map:
                default_progress = status_progress_map[current_status]
                if default_progress > self.last_progress:
                    progress = default_progress

            # If still no progress value, increment by a small amount
            if progress is None and self.last_progress < 99:
                progress = min(self.last_progress + 1, 99)  # Don't go over 99

        # Only update progress if it has increased
        if progress is not None and progress > self.last_progress:
            self.last_progress = progress
        else:
            # No progress update needed, keep the existing value
            progress = None

        # Update the job status with the latest message
        update_job_status(
            self.job_id,
            jobs[self.job_id]["status"],
            progress=progress,
            current_activity=most_recent,
        )

        # Reset for next batch
        self.last_update_time = time.time()
        self.batched_messages = []

    def flush(self):
        self.old_stdout.flush()


# Background processing function
async def process_video(
    job_id: str,
    video_path: str,
    voice_id: str,
    elevenlabs_api_key: str,
    speed_factor: float = 1.0,
):
    """Process the uploaded video in the background."""
    # Set up progress capture
    with ProgressCapture(job_id) as progress_capture:
        try:
            # Update job status
            logger.info(f"[Job {job_id}] Starting processing: extracting audio")
            update_job_status(
                job_id,
                "extracting_audio",
                progress=10,
                speed_factor=speed_factor,
                current_activity="Starting audio extraction from video",
            )

            # Allow other tasks (like WebSocket broadcasts) to run
            await asyncio.sleep(0.1)

            # Step 1: Extract audio from video
            audio_path = os.path.join(TEMP_DIR, f"{job_id}_audio.wav")
            extract_audio_from_video(video_path, audio_path)

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Update job status
            logger.info(f"[Job {job_id}] Audio extracted, now transcribing")
            update_job_status(
                job_id,
                "transcribing",
                progress=20,
                audio_path=audio_path,
                current_activity="Transcribing audio with Whisper AI",
            )

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Step 2: Transcribe audio to get segments
            segments = transcribe_audio(audio_path, model_size="base")

            if not segments:
                raise Exception("No speech detected in the video")

            # Save SRT file
            srt_path = os.path.join(TEMP_DIR, f"{job_id}_subtitles.srt")
            save_srt_file(segments, srt_path)

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Update job status with transcription segments
            logger.info(f"[Job {job_id}] Transcription complete, waiting for review")
            update_job_status(
                job_id,
                "transcription_complete",
                progress=40,
                transcription=segments,
                srt_path=srt_path,
                current_activity="Transcription ready for review",
            )

            # At this point, we need to exit the function and wait for the user to confirm
            # the transcription by calling the update_job_transcription endpoint
            logger.info(
                f"[Job {job_id}] Process paused waiting for user transcription review"
            )
            return

            # The following code will only execute when the update_job_transcription
            # endpoint is called and the job status is updated to "transcription_confirmed"
            # This part is handled separately in the update_job_transcription endpoint

            # Step 3: Generate TTS for each segment
            os.environ["ELEVENLABS_API_KEY"] = elevenlabs_api_key

            # Log a masked version of the API key for debugging
            masked_key = (
                elevenlabs_api_key[:4]
                + "*" * (len(elevenlabs_api_key) - 8)
                + elevenlabs_api_key[-4:]
                if len(elevenlabs_api_key) > 8
                else "***"
            )
            logger.info(f"[Job {job_id}] Using ElevenLabs API Key: {masked_key}")
            logger.info(
                f"[Job {job_id}] Generating TTS with ElevenLabs (speed factor: {speed_factor})"
            )
            update_job_status(
                job_id,
                "generating_tts",
                progress=50,
                current_activity=f"Generating AI voiceover with speed factor {speed_factor}",
            )

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            tts_clips_info = generate_tts_for_segments(
                segments, voice_id, VOICE_SETTINGS, TEMP_DIR, speed_factor
            )

            if not tts_clips_info:
                raise Exception("Failed to generate TTS audio")

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Step 4: Create composite voiceover track
            logger.info(f"[Job {job_id}] Creating composite voiceover track")
            update_job_status(
                job_id,
                "creating_voiceover",
                progress=80,
                current_activity="Assembling audio segments into complete voiceover",
            )

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Get video duration
            from moviepy.editor import VideoFileClip

            video_clip = VideoFileClip(video_path)
            video_duration = video_clip.duration
            video_clip.close()

            voiceover_track = create_composite_voiceover(tts_clips_info, video_duration)

            # Ensure the voiceover track has an fps attribute for saving as MP3
            if not hasattr(voiceover_track, "fps") or voiceover_track.fps is None:
                logger.info("Setting default fps=44100 on voiceover track")
                voiceover_track.fps = 44100

            # Save audio-only file
            audio_output_path = os.path.join(OUTPUT_DIR, f"{job_id}_audio_only.mp3")
            voiceover_track.write_audiofile(
                audio_output_path, codec="mp3", verbose=False, logger=None
            )

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Step 5: Create final video
            logger.info(f"[Job {job_id}] Creating final video")
            update_job_status(
                job_id,
                "creating_video",
                progress=90,
                current_activity="Creating final video with voiceover",
            )

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            output_video_path = os.path.join(OUTPUT_DIR, f"{job_id}_output.mp4")
            create_final_video(video_path, voiceover_track, output_video_path)

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Mark job as completed
            logger.info(f"[Job {job_id}] Processing completed successfully")
            update_job_status(
                job_id,
                "completed",
                progress=100,
                finished_at=datetime.now().isoformat(),
                video_path=f"/media/outputs/{job_id}_output.mp4",
                audio_path=f"/media/outputs/{job_id}_audio_only.mp3",
                speed_factor=speed_factor,
                current_activity="Processing completed successfully",
            )

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            update_job_status(
                job_id,
                "error",
                progress=0,
                error=str(e),
                finished_at=datetime.now().isoformat(),
                current_activity=f"Error: {str(e)}",
            )


def is_valid_elevenlabs_api_key(api_key):
    """Basic validation for ElevenLabs API key format."""
    # ElevenLabs API keys are typically 32 character strings
    if not api_key or len(api_key) < 32:
        return False

    # Most API keys start with a specific prefix (could be updated based on actual format)
    # if not api_key.startswith("el_"):
    #    return False

    return True


# Endpoints
@app.get("/")
async def read_root():
    return {"message": "Welcome to AutoDubber API"}


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    logger.info(f"New WebSocket connection request for job {job_id}")
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for job {job_id}")

    # Add the connection to the list for this job
    if job_id not in active_connections:
        active_connections[job_id] = []
    active_connections[job_id].append(websocket)
    logger.info(
        f"Added WebSocket connection to active_connections for job {job_id}, total connections: {len(active_connections[job_id])}"
    )

    # Create a background task for ping-pong to keep connection alive
    ping_task = None

    try:
        # Send current job status if available
        if job_id in jobs:
            logger.info(
                f"Sending initial job status: {jobs[job_id].get('status')} for job {job_id}"
            )

            # Ensure a valid current_activity is set
            if not jobs[job_id].get("current_activity"):
                status = jobs[job_id].get("status")
                if status in statusMessages:
                    jobs[job_id]["current_activity"] = statusMessages[status]
                else:
                    jobs[job_id]["current_activity"] = f"Processing in {status} stage"

            # Send the complete job state
            await websocket.send_json(jobs[job_id])

            # Force a progress update event for any job in progress
            current_status = jobs[job_id].get("status")
            if current_status not in ["completed", "error"]:
                logger.info(
                    f"Job {job_id} is in progress, sending immediate status update"
                )
                # Minor update to progress to trigger frontend refresh
                if "progress" in jobs[job_id]:
                    # Small increment to trigger UI update but not disrupt existing progress
                    progress_increment = min(
                        1.0, (100 - jobs[job_id]["progress"]) * 0.05
                    )
                    jobs[job_id]["progress"] += progress_increment

                # Send updated job state
                await websocket.send_json(jobs[job_id])
        else:
            logger.warning(f"No job record found for job_id {job_id}")

        # Start ping task to keep connection alive
        ping_task = asyncio.create_task(keep_connection_alive(websocket, job_id))

        # Keep the connection open and handle incoming messages
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message for job {job_id}: {data[:100]}")
            message = json.loads(data)

            # Handle transcription update
            if message.get("action") == "update_transcription" and job_id in jobs:
                logger.info(f"Received transcription update for job {job_id}")
                updated_transcription = message.get("transcription")
                speed_factor = message.get(
                    "speed_factor", 1.0
                )  # Get speed factor with default 1.0

                if updated_transcription:
                    jobs[job_id]["transcription"] = updated_transcription
                    jobs[job_id]["status"] = "transcription_confirmed"
                    jobs[job_id]["progress"] = 45
                    jobs[job_id][
                        "current_activity"
                    ] = "Transcription confirmed, proceeding with voiceover generation"

                    # Store the speed factor in the job
                    if speed_factor:
                        jobs[job_id]["speed_factor"] = speed_factor
                        logger.info(
                            f"Updated speed factor for job {job_id} to {speed_factor}"
                        )

                    logger.info(
                        f"Updated transcription for job {job_id}, broadcasting update"
                    )
                    await broadcast_job_update(job_id, jobs[job_id])

    except WebSocketDisconnect:
        # Remove the connection when it's closed
        logger.info(f"WebSocket disconnected for job {job_id}")
        if job_id in active_connections:
            active_connections[job_id].remove(websocket)
            logger.info(
                f"Removed WebSocket connection for job {job_id}, remaining connections: {len(active_connections[job_id])}"
            )
            if not active_connections[job_id]:
                del active_connections[job_id]
                logger.info(f"Deleted empty connections list for job {job_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection for job {job_id}: {str(e)}")
        if job_id in active_connections and websocket in active_connections[job_id]:
            active_connections[job_id].remove(websocket)
            if not active_connections[job_id]:
                del active_connections[job_id]
    finally:
        # Cancel ping task if it exists
        if ping_task:
            ping_task.cancel()


# Websocket keep-alive ping function
async def keep_connection_alive(websocket: WebSocket, job_id: str):
    """Send periodic pings to keep WebSocket connection alive"""
    ping_interval = 5  # seconds (reduced from 10s for more frequent pings)
    try:
        while True:
            await asyncio.sleep(ping_interval)
            try:
                # If job exists, send current status as a heartbeat
                if job_id in jobs:
                    logger.debug(f"Sending heartbeat ping for job {job_id}")

                    # Get current job status
                    current_status = jobs[job_id].get("status")
                    current_progress = jobs[job_id].get("progress", 0)
                    current_activity = jobs[job_id].get("current_activity", "")

                    # Send a more detailed ping with current job state
                    await websocket.send_json(
                        {
                            "type": "ping",
                            "job_id": job_id,
                            "status": current_status,
                            "progress": current_progress,
                            "current_activity": current_activity,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                    # For jobs in progress, periodically resend the full job state
                    # This helps ensure frontend stays in sync
                    if (
                        current_status not in ["completed", "error"]
                        and random.random() < 0.3
                    ):  # 30% chance
                        logger.debug(
                            f"Sending periodic full state update for job {job_id}"
                        )
                        await websocket.send_json(jobs[job_id])
                else:
                    # Simple ping if no job data
                    await websocket.send_json(
                        {"type": "ping", "timestamp": datetime.now().isoformat()}
                    )
            except Exception as e:
                logger.error(
                    f"Error sending ping to WebSocket for job {job_id}: {str(e)}"
                )
                break
    except asyncio.CancelledError:
        logger.debug(f"Ping task for job {job_id} cancelled")
        pass


@app.post("/upload-video")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    voice_id: str = Form("21m00Tcm4TlvDq8ikWAM"),  # Rachel voice default
    elevenlabs_api_key: str = Form(None),
    speed_factor: float = Form(1.0),  # Default speed factor (1.0 = normal speed)
    xi_api_key: str = Header(None, alias="xi-api-key"),
):
    # Use the header API key if provided, otherwise fall back to form data
    api_key = xi_api_key or elevenlabs_api_key

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="ElevenLabs API key is required. Provide it via 'xi-api-key' header or form field.",
        )

    # Validate speed factor
    if speed_factor < 0.7 or speed_factor > 1.2:
        raise HTTPException(
            status_code=400,
            detail="Speed factor must be between 0.7 and 1.2.",
        )

    # Log a masked version of the API key for debugging
    masked_key = (
        api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        if len(api_key) > 8
        else "***"
    )
    logger.info(
        f"Upload video with ElevenLabs API Key: {masked_key}, speed factor: {speed_factor}"
    )

    # Validate API key
    if not is_valid_elevenlabs_api_key(api_key):
        logger.error(f"Invalid API key format: {masked_key}")
        raise HTTPException(
            status_code=400,
            detail="Invalid ElevenLabs API key format. Please provide a valid API key.",
        )

    # Validate file
    if not file.filename.lower().endswith((".mp4", ".mov", ".avi", ".webm")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload MP4, MOV, AVI, or WEBM.",
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Save uploaded file to disk
    file_location = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create job record with initial status
    job = {
        "job_id": job_id,
        "filename": file.filename,
        "status": "uploaded",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "voice_id": voice_id,
        "speed_factor": speed_factor,
        "current_activity": "File uploaded, waiting to start processing",
        "_elevenlabs_api_key": api_key,  # Store API key for later use (secure in production)
    }
    jobs[job_id] = job

    # Broadcast the initial job status
    asyncio.create_task(run_broadcast(job_id, job))

    # Start background processing
    background_tasks.add_task(
        process_video, job_id, file_location, voice_id, api_key, speed_factor
    )

    logger.info(f"Started background processing for job {job_id}")

    return {"job_id": job_id, "status": "Processing started"}


@app.get("/jobs")
async def get_all_jobs():
    """Return all jobs."""
    return jobs


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Return details for a specific job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.post("/jobs/{job_id}/update-transcription")
async def update_job_transcription(job_id: str, transcription: List[Dict[str, Any]]):
    """Update the transcription for a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    if jobs[job_id]["status"] != "transcription_complete":
        raise HTTPException(status_code=400, detail="Job not in transcription phase")

    # Update transcription
    jobs[job_id]["transcription"] = transcription

    # Update SRT file
    srt_path = os.path.join(TEMP_DIR, f"{job_id}_subtitles.srt")
    save_srt_file(transcription, srt_path)

    # Update job status to indicate transcription is confirmed
    update_job_status(
        job_id,
        "transcription_confirmed",
        progress=45,
        current_activity="Transcription confirmed, proceeding with voiceover generation",
    )

    # Get the necessary job data to resume processing
    job_data = jobs[job_id]
    voice_id = job_data.get("voice_id")
    speed_factor = job_data.get("speed_factor", 1.0)

    # Get the video path
    video_path = None
    for file in os.listdir(UPLOAD_DIR):
        if file.startswith(job_id + "_"):
            video_path = os.path.join(UPLOAD_DIR, file)
            break

    if not video_path:
        raise HTTPException(
            status_code=404, detail="Original video file not found for this job"
        )

    # Get the API key (in a real-world app, this would be stored securely)
    elevenlabs_api_key = job_data.get("_elevenlabs_api_key")
    if not elevenlabs_api_key:
        raise HTTPException(status_code=500, detail="API key not available")

    # Start the continuation of video processing in the background
    asyncio.create_task(
        continue_video_processing(
            job_id,
            video_path,
            voice_id,
            elevenlabs_api_key,
            speed_factor,
            transcription,
        )
    )

    return {"status": "Transcription updated, processing resumed"}


async def continue_video_processing(
    job_id: str,
    video_path: str,
    voice_id: str,
    elevenlabs_api_key: str,
    speed_factor: float = 1.0,
    transcription: List[Dict[str, Any]] = None,
):
    """Continue processing the video after transcription has been confirmed."""
    # Set up progress capture
    with ProgressCapture(job_id) as progress_capture:
        try:
            # Step 3: Generate TTS for each segment
            os.environ["ELEVENLABS_API_KEY"] = elevenlabs_api_key

            # Log a masked version of the API key for debugging
            masked_key = (
                elevenlabs_api_key[:4]
                + "*" * (len(elevenlabs_api_key) - 8)
                + elevenlabs_api_key[-4:]
                if len(elevenlabs_api_key) > 8
                else "***"
            )
            logger.info(f"[Job {job_id}] Using ElevenLabs API Key: {masked_key}")
            logger.info(
                f"[Job {job_id}] Generating TTS with ElevenLabs (speed factor: {speed_factor})"
            )
            update_job_status(
                job_id,
                "generating_tts",
                progress=50,
                current_activity=f"Generating AI voiceover with speed factor {speed_factor}",
            )

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Use the updated transcription
            segments = transcription

            tts_clips_info = generate_tts_for_segments(
                segments, voice_id, VOICE_SETTINGS, TEMP_DIR, speed_factor
            )

            if not tts_clips_info:
                raise Exception("Failed to generate TTS audio")

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Step 4: Create composite voiceover track
            logger.info(f"[Job {job_id}] Creating composite voiceover track")
            update_job_status(
                job_id,
                "creating_voiceover",
                progress=80,
                current_activity="Assembling audio segments into complete voiceover",
            )

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Get video duration
            from moviepy.editor import VideoFileClip

            video_clip = VideoFileClip(video_path)
            video_duration = video_clip.duration
            video_clip.close()

            voiceover_track = create_composite_voiceover(tts_clips_info, video_duration)

            # Ensure the voiceover track has an fps attribute for saving as MP3
            if not hasattr(voiceover_track, "fps") or voiceover_track.fps is None:
                logger.info("Setting default fps=44100 on voiceover track")
                voiceover_track.fps = 44100

            # Save audio-only file
            audio_output_path = os.path.join(OUTPUT_DIR, f"{job_id}_audio_only.mp3")
            voiceover_track.write_audiofile(
                audio_output_path, codec="mp3", verbose=False, logger=None
            )

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Step 5: Create final video
            logger.info(f"[Job {job_id}] Creating final video")
            update_job_status(
                job_id,
                "creating_video",
                progress=90,
                current_activity="Creating final video with voiceover",
            )

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            output_video_path = os.path.join(OUTPUT_DIR, f"{job_id}_output.mp4")
            create_final_video(video_path, voiceover_track, output_video_path)

            # Allow other tasks to run
            await asyncio.sleep(0.1)

            # Mark job as completed
            logger.info(f"[Job {job_id}] Processing completed successfully")
            update_job_status(
                job_id,
                "completed",
                progress=100,
                finished_at=datetime.now().isoformat(),
                video_path=f"/media/outputs/{job_id}_output.mp4",
                audio_path=f"/media/outputs/{job_id}_audio_only.mp3",
                speed_factor=speed_factor,
                current_activity="Processing completed successfully",
            )

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            update_job_status(
                job_id,
                "error",
                progress=0,
                error=str(e),
                finished_at=datetime.now().isoformat(),
                current_activity=f"Error: {str(e)}",
            )


@app.get("/voices")
async def get_voices(elevenlabs_api_key: str = Header(None, alias="xi-api-key")):
    """Get available ElevenLabs voices."""
    try:
        # Validate API key
        if not is_valid_elevenlabs_api_key(elevenlabs_api_key):
            masked_key = (
                elevenlabs_api_key[:4]
                + "*" * (len(elevenlabs_api_key) - 8)
                + elevenlabs_api_key[-4:]
                if len(elevenlabs_api_key) > 8
                else "***"
            )
            logger.error(f"Invalid API key format: {masked_key}")
            raise HTTPException(
                status_code=400,
                detail="Invalid ElevenLabs API key format. Please provide a valid API key.",
            )

        # Temporarily set the API key in the environment
        os.environ["ELEVENLABS_API_KEY"] = elevenlabs_api_key

        # Log a masked version of the API key for debugging
        masked_key = (
            elevenlabs_api_key[:4]
            + "*" * (len(elevenlabs_api_key) - 8)
            + elevenlabs_api_key[-4:]
            if len(elevenlabs_api_key) > 8
            else "***"
        )
        logger.info(f"Fetching voices using ElevenLabs API Key: {masked_key}")

        # This function returns the actual objects, but we need serializable data
        all_voices = list_available_voices()

        # Convert to serializable format
        voice_data = [
            {
                "voice_id": voice.voice_id,
                "name": voice.name,
                "preview_url": voice.preview_url,
                "description": voice.description,
                "category": voice.category,
            }
            for voice in all_voices
        ]

        return voice_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching voices: {str(e)}")


@app.post("/jobs/{job_id}/adjust-speed")
async def adjust_audio_speed(
    job_id: str, background_tasks: BackgroundTasks, speed_factor: float = Form(...)
):
    """Adjust the speed of the audio and regenerate the output files."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    if jobs[job_id]["status"] != "completed":
        raise HTTPException(
            status_code=400, detail="Job must be completed before adjusting speed"
        )

    if speed_factor <= 0:
        raise HTTPException(
            status_code=400, detail="Speed factor must be greater than 0"
        )

    # Get the path to the original generated audio
    audio_path = jobs[job_id].get("audio_path")
    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio file not found for this job")

    # Get the path to the video
    video_path = None
    for file in os.listdir(UPLOAD_DIR):
        if file.startswith(job_id + "_"):
            video_path = os.path.join(UPLOAD_DIR, file)
            break

    if not video_path:
        raise HTTPException(
            status_code=404, detail="Original video file not found for this job"
        )

    # Extract the relative path and convert to local path
    audio_rel_path = audio_path.replace("/media/outputs/", "")
    audio_abs_path = os.path.join(OUTPUT_DIR, audio_rel_path)

    # Update job status
    update_job_status(job_id, "adjusting_speed", progress=0)

    # Process in background
    background_tasks.add_task(
        process_speed_adjustment, job_id, audio_abs_path, video_path, speed_factor
    )

    return {"status": "Speed adjustment started", "job_id": job_id}


async def process_speed_adjustment(
    job_id: str, audio_path: str, video_path: str, speed_factor: float
):
    """Process the speed adjustment in the background."""
    # Set up progress capture
    with ProgressCapture(job_id) as progress_capture:
        try:
            # Update job status
            update_job_status(
                job_id,
                "adjusting_speed",
                progress=10,
                current_activity=f"Adjusting audio speed to {speed_factor*100}%",
            )

            logger.info(
                f"[Job {job_id}] Adjusting audio speed with factor: {speed_factor}"
            )

            # Import here to avoid circular imports
            from moviepy.editor import AudioFileClip, VideoFileClip

            # Load the audio file
            audio_clip = AudioFileClip(audio_path)

            # Adjust the speed
            from moviepy.audio.fx.all import speedx

            adjusted_audio = audio_clip.fx(speedx, speed_factor)

            # Save the adjusted audio
            adjusted_audio_path = os.path.join(
                OUTPUT_DIR, f"{job_id}_speed_{speed_factor}_audio.mp3"
            )
            adjusted_audio.write_audiofile(
                adjusted_audio_path, codec="mp3", verbose=False, logger=None
            )

            # Update progress
            update_job_status(
                job_id,
                "creating_adjusted_video",
                progress=50,
                current_activity="Creating new video with adjusted audio speed",
            )

            # Create a new video with the adjusted audio
            video_clip = VideoFileClip(video_path)
            final_clip = video_clip.set_audio(adjusted_audio)

            # Save the adjusted video
            adjusted_video_path = os.path.join(
                OUTPUT_DIR, f"{job_id}_speed_{speed_factor}_video.mp4"
            )
            final_clip.write_videofile(
                adjusted_video_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=os.path.join(TEMP_DIR, f"{job_id}_temp_audio.m4a"),
                remove_temp=True,
                verbose=False,
                logger=None,
            )

            # Close the clips to release resources
            audio_clip.close()
            adjusted_audio.close()
            video_clip.close()
            final_clip.close()

            # Update job status with new paths
            update_job_status(
                job_id,
                "completed",
                progress=100,
                audio_path=f"/media/outputs/{job_id}_speed_{speed_factor}_audio.mp3",
                video_path=f"/media/outputs/{job_id}_speed_{speed_factor}_video.mp4",
                speed_factor=speed_factor,
                current_activity=f"Speed adjustment completed successfully",
            )

            logger.info(f"[Job {job_id}] Speed adjustment completed successfully")

        except Exception as e:
            logger.error(f"Error adjusting speed for job {job_id}: {str(e)}")
            update_job_status(
                job_id,
                "error",
                progress=0,
                error=f"Speed adjustment failed: {str(e)}",
                current_activity=f"Error: Speed adjustment failed - {str(e)}",
            )


@app.get("/file-path/{file_type}/{job_id}")
async def get_file_path(file_type: str, job_id: str):
    """Return the relative URL path for a media file, suitable for constructing a download link."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_data = jobs[job_id]
    path_value = None

    if file_type == "video":
        path_value = job_data.get(
            "video_path"
        )  # Should be like /media/outputs/filename.mp4
    elif file_type == "audio":
        path_value = job_data.get(
            "audio_path"
        )  # Should be like /media/outputs/filename.mp3
    elif file_type == "srt":
        abs_srt_path = job_data.get(
            "srt_path"
        )  # This is stored as an absolute system path
        if abs_srt_path:
            filename = os.path.basename(abs_srt_path)
            path_value = f"/media/temp/{filename}"  # Convert to relative URL /media/temp/filename.srt
    else:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Use 'video', 'audio', or 'srt'"
        )

    if not path_value:
        raise HTTPException(
            status_code=404, detail=f"Path for {file_type} not found for job {job_id}"
        )

    # Ensure the path is a relative media URL
    if not path_value.startswith("/media/"):
        logger.error(
            f"Path for {file_type} in job {job_id} is not a valid relative media URL: {path_value}"
        )
        # Attempt to recover if it's an absolute path that maps to a known media dir
        # This is a fallback, ideally paths are stored correctly.
        media_root = os.path.abspath(os.path.join(os.getcwd(), "media"))
        abs_path_value = os.path.abspath(path_value)

        if abs_path_value.startswith(os.path.join(media_root, "outputs")):
            path_value = "/media/outputs/" + os.path.basename(abs_path_value)
        elif abs_path_value.startswith(os.path.join(media_root, "temp")):
            path_value = "/media/temp/" + os.path.basename(abs_path_value)
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Internal error generating path for {file_type}: Invalid path structure.",
            )

    logger.info(f"Returning path for {file_type}, job {job_id}: {path_value}")
    return {"path": path_value}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
