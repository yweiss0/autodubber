import os
import sys
import tempfile
import argparse
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
import whisper  # openai-whisper
from elevenlabs import generate, set_api_key, voices, Voice, VoiceSettings
from dotenv import load_dotenv
import time

# --- Configuration ---
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    print("ELEVENLABS_API_KEY not found in .env file or environment variables.")
    print(
        "Please create a .env file with your API key or set it as an environment variable."
    )
    print("Example: ELEVENLABS_API_KEY=your_api_key_here")
    sys.exit(1)

set_api_key(ELEVENLABS_API_KEY)

# Default voice ID - Justin
DEFAULT_VOICE_ID = "uYkKk3J4lEp7IHQ8CLBi"  # Justin voice ID

# Voice settings
VOICE_SETTINGS = VoiceSettings(
    stability=0.7,  # Lower for more expressiveness, higher for more consistency
    similarity_boost=0.75,  # Higher for closer match to original voice (if cloning)
    style=0.0,  # For style transfer if using v2 models, 0 for no style
    use_speaker_boost=True,
    speed=1.0,  # Default speed, 1.0 is normal speed, can be 0.7-1.2
)


# --- Helper Functions ---


def extract_audio_from_video(video_path, audio_output_path):
    """Extract audio from video file"""
    print(f"PROGRESS_UPDATE: Extracting audio from video file: {video_path}...")
    try:
        print(f"PROGRESS_UPDATE: Loading video file...")
        video_clip = VideoFileClip(video_path)
        audio_clip = video_clip.audio
        if audio_clip:
            print(f"PROGRESS_UPDATE: Writing audio to file...")
            audio_clip.write_audiofile(
                audio_output_path, codec="pcm_s16le", verbose=False, logger=None
            )  # WAV for best Whisper quality
            audio_clip.close()
        else:
            raise ValueError("Video has no audio track.")
        video_clip.close()
        print(f"PROGRESS_UPDATE: Audio extraction completed: {audio_output_path}")
        return audio_output_path
    except Exception as e:
        print(f"ERROR: Audio extraction failed: {str(e)}")
        raise


def transcribe_audio(audio_path, model_size="base"):
    """Transcribe audio using Whisper"""
    print(f"PROGRESS_UPDATE: Loading Whisper {model_size} model...")
    try:
        model = whisper.load_model(model_size)
        print("PROGRESS_UPDATE: Whisper model loaded, beginning transcription...")

        # Add a progress indicator for transcription start
        print("PROGRESS_UPDATE: Transcribing audio with Whisper AI...")

        result = model.transcribe(
            audio_path, verbose=False, fp16=False
        )  # fp16=False for CPU, True for GPU if available

        print("PROGRESS_UPDATE: Transcription completed successfully.")
        return result[
            "segments"
        ]  # List of dicts: {'id', 'seek', 'start', 'end', 'text', ...}
    except Exception as e:
        print(f"ERROR: Transcription failed: {str(e)}")
        raise


def save_srt_file(segments, output_srt_path):
    """Save segments as SRT file"""
    print(f"PROGRESS_UPDATE: Saving transcription to SRT file: {output_srt_path}...")
    try:
        with open(output_srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments):
                start_t = whisper.utils.format_timestamp(
                    seg["start"], always_include_hours=True, decimal_marker=","
                )
                end_t = whisper.utils.format_timestamp(
                    seg["end"], always_include_hours=True, decimal_marker=","
                )
                f.write(f"{i+1}\n{start_t} --> {end_t}\n{seg['text'].strip()}\n\n")
        print(f"PROGRESS_UPDATE: SRT file saved successfully")
    except Exception as e:
        print(f"ERROR: SRT file save failed: {str(e)}")
        # Continue execution even if SRT save fails


def generate_tts_for_segments(
    segments, voice_id, voice_settings, temp_dir, speed_factor=1.0
):
    """Generates TTS for each segment and returns a list of segment info dictionaries"""
    print(
        f"PROGRESS_UPDATE: Generating TTS with ElevenLabs voice ID {voice_id} (speed factor: {speed_factor})"
    )
    tts_clips_info = []

    # Apply speed to voice settings
    # Create a new voice settings object with the specified speed
    settings_with_speed = VoiceSettings(
        stability=voice_settings.stability,
        similarity_boost=voice_settings.similarity_boost,
        style=voice_settings.style if hasattr(voice_settings, "style") else 0.0,
        use_speaker_boost=(
            voice_settings.use_speaker_boost
            if hasattr(voice_settings, "use_speaker_boost")
            else True
        ),
        speed=speed_factor,  # Apply the requested speed factor
    )

    # Count total characters for estimation
    total_chars = sum(len(segment["text"].strip()) for segment in segments)
    processed_chars = 0
    start_time = time.time()

    print(
        f"PROGRESS_UPDATE: Starting TTS generation for {len(segments)} segments, {total_chars} total characters"
    )

    for i, segment in enumerate(segments):
        text = segment["text"].strip()
        start_time_sec = segment["start"]  # seconds
        end_time_sec = segment["end"]  # seconds

        # Progress reporting
        processed_chars += len(text)
        progress = processed_chars / total_chars * 100 if total_chars > 0 else 0
        elapsed = time.time() - start_time

        # Calculate segment percentage for better tracking
        segment_percent = (i + 1) / len(segments) * 100

        print(
            f"PROGRESS_UPDATE: TTS generating segment {i+1}/{len(segments)} [{progress:.1f}%] (segment {segment_percent:.0f}%) - \"{text[:50]}{'...' if len(text) > 50 else ''}\""
        )

        if not text:
            print(f"PROGRESS_UPDATE: Skipping empty segment {i+1}")
            continue

        try:
            # Generate audio using the specific voice and settings with speed factor
            audio_data = generate(
                text=text,
                voice=Voice(voice_id=voice_id, settings=settings_with_speed),
                model="eleven_multilingual_v2",  # or "eleven_monolingual_v1"
            )
            segment_audio_path = os.path.join(temp_dir, f"segment_{i:04d}.mp3")
            with open(segment_audio_path, "wb") as f:
                f.write(audio_data)
            tts_clips_info.append(
                {
                    "start": start_time_sec,
                    "end": end_time_sec,
                    "path": segment_audio_path,
                    "text": text,
                }
            )

            # Estimate remaining time
            if processed_chars > 0 and elapsed > 0:
                chars_per_second = processed_chars / elapsed
                remaining_chars = total_chars - processed_chars
                remaining_time = (
                    remaining_chars / chars_per_second if chars_per_second > 0 else 0
                )
                print(
                    f"PROGRESS_UPDATE: Estimated TTS time remaining: {remaining_time:.1f} seconds"
                )

        except Exception as e:
            print(f"ERROR: TTS generation failed for segment {i+1}: {str(e)}")
            continue

    print(
        f"PROGRESS_UPDATE: TTS generation complete for all {len(segments)} segments, total {processed_chars} characters"
    )
    return tts_clips_info


def create_composite_voiceover(tts_clips_info, total_duration):
    """Creates a single voiceover track from individual TTS clips, respecting original timing"""
    print("PROGRESS_UPDATE: Creating composite voiceover track from segments...")
    if not tts_clips_info:
        print("WARNING: No TTS clips to composite. Returning empty audio.")
        return AudioFileClip(duration=total_duration, fps=44100)

    final_audio_segments = []

    # Default fps value to use
    default_fps = 44100  # Standard audio sampling rate

    print(
        f"PROGRESS_UPDATE: Processing {len(tts_clips_info)} audio segments for composition"
    )

    for i, clip_info in enumerate(tts_clips_info):
        try:
            print(
                f"PROGRESS_UPDATE: Adding audio segment {i+1}/{len(tts_clips_info)} to voiceover (starts at {clip_info['start']:.2f}s)"
            )
            audio_segment = AudioFileClip(clip_info["path"])
            # Set the start time of this clip in the composite audio
            audio_segment = audio_segment.set_start(clip_info["start"])
            final_audio_segments.append(audio_segment)
        except Exception as e:
            print(
                f"ERROR: Failed to add segment starting at {clip_info['start']}: {str(e)}"
            )
            continue

    # Create the composite audio
    print(
        f"PROGRESS_UPDATE: Compositing {len(final_audio_segments)} audio segments into final voiceover track"
    )
    composite_audio = CompositeAudioClip(final_audio_segments)

    # Explicitly set fps attribute which is required by some operations
    if not hasattr(composite_audio, "fps") or composite_audio.fps is None:
        print(
            f"PROGRESS_UPDATE: Setting default audio sampling rate to {default_fps}Hz"
        )
        composite_audio.fps = default_fps

    # Ensure the composite audio has a defined duration
    max_end_time = 0
    if final_audio_segments:
        for clip in final_audio_segments:
            clip_end = clip.start + clip.duration
            if clip_end > max_end_time:
                max_end_time = clip_end

    final_duration = max(total_duration, max_end_time)
    composite_audio = composite_audio.set_duration(final_duration)

    print(
        f"PROGRESS_UPDATE: Voiceover assembly completed. Duration: {composite_audio.duration:.2f}s"
    )
    return composite_audio


def create_final_video(original_video_path, voiceover_audio_clip, output_video_path):
    """Create final video with new audio"""
    print(f"PROGRESS_UPDATE: Creating final video with voiceover: {output_video_path}")
    try:
        print(
            f"PROGRESS_UPDATE: Loading original video for processing: {original_video_path}"
        )
        original_video = VideoFileClip(original_video_path)

        # Mute original video
        print(f"PROGRESS_UPDATE: Muting original video audio track")
        video_muted = original_video.without_audio()

        # Ensure audio clip has fps attribute
        if not hasattr(voiceover_audio_clip, "fps") or voiceover_audio_clip.fps is None:
            print("PROGRESS_UPDATE: Setting default audio sampling rate to 44100Hz")
            voiceover_audio_clip.fps = 44100

        # Set the new voiceover
        print(f"PROGRESS_UPDATE: Applying new voiceover audio to video")
        final_video = video_muted.set_audio(voiceover_audio_clip)

        # Ensure the voiceover duration doesn't exceed video duration
        if final_video.audio and final_video.audio.duration > final_video.duration:
            print(
                f"PROGRESS_UPDATE: Trimming audio to match video duration ({final_video.duration:.2f}s)"
            )
            final_video.audio = final_video.audio.subclip(0, final_video.duration)

        # Write the result to a file
        print("PROGRESS_UPDATE: Encoding final video (this may take a while)...")
        final_video.write_videofile(
            output_video_path,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="medium",
            verbose=False,
            logger=None,
        )

        # Clean up
        print("PROGRESS_UPDATE: Closing video and audio objects")
        original_video.close()
        video_muted.close()
        if voiceover_audio_clip and hasattr(voiceover_audio_clip, "close"):
            voiceover_audio_clip.close()
        final_video.close()

        print("PROGRESS_UPDATE: Final video creation completed successfully!")
    except Exception as e:
        print(f"ERROR: Video creation failed: {str(e)}")
        # Clean up if possible
        if "original_video" in locals() and hasattr(original_video, "close"):
            original_video.close()
        if "video_muted" in locals() and hasattr(video_muted, "close"):
            video_muted.close()
        if "voiceover_audio_clip" in locals() and hasattr(
            voiceover_audio_clip, "close"
        ):
            voiceover_audio_clip.close()
        if "final_video" in locals() and hasattr(final_video, "close"):
            final_video.close()
        raise


def list_available_voices():
    """List available ElevenLabs voices"""
    try:
        available_voices = voices()
        print("\nAvailable ElevenLabs voices:")
        for voice in available_voices:
            print(f"  ID: {voice.voice_id} | Name: {voice.name}")
        print("\nUse these voice IDs with the --voice-id parameter")
        return available_voices
    except Exception as e:
        print(f"Error fetching voices: {str(e)}")
        return []


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Create a video with ElevenLabs TTS voiceover from transcribed content"
    )

    parser.add_argument("input_video", help="Path to the input video file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the output video file",
        default="output_with_voiceover.mp4",
    )
    parser.add_argument(
        "-m",
        "--model",
        help="Whisper model size",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
    )
    parser.add_argument(
        "-l", "--language", help="Language code (e.g., 'en' for English)", default=None
    )
    parser.add_argument(
        "-v", "--voice-id", help="ElevenLabs voice ID", default=DEFAULT_VOICE_ID
    )
    parser.add_argument("-s", "--srt", help="Save SRT file", action="store_true")
    parser.add_argument(
        "--list-voices", help="List available ElevenLabs voices", action="store_true"
    )

    return parser.parse_args()


# --- Main Execution ---
if __name__ == "__main__":
    args = parse_arguments()

    if args.list_voices:
        list_available_voices()
        sys.exit(0)

    input_video = args.input_video
    output_video = args.output
    model_size = args.model
    if args.language:
        model_size = f"{model_size}.{args.language}"

    if not os.path.exists(input_video):
        print(f"Error: Input video '{input_video}' not found.")
        sys.exit(1)

    # Create a temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Temporary directory: {temp_dir}")

        try:
            # 1. Extract audio
            extracted_audio_path = os.path.join(temp_dir, "extracted_audio.wav")
            extract_audio_from_video(input_video, extracted_audio_path)

            # 2. Transcribe to get segments (text with timestamps)
            segments = transcribe_audio(extracted_audio_path, model_size=model_size)

            if not segments:
                print("No segments transcribed. Exiting.")
                sys.exit(1)

            # Optionally save SRT
            if args.srt:
                srt_path = os.path.splitext(output_video)[0] + ".srt"
                save_srt_file(segments, srt_path)

            # 3. Generate TTS for each segment
            tts_clips_info = generate_tts_for_segments(
                segments, args.voice_id, VOICE_SETTINGS, temp_dir
            )

            if not tts_clips_info:
                print("No TTS clips were generated. The final video will be silent.")
                original_video_for_duration = VideoFileClip(input_video)
                video_duration = original_video_for_duration.duration
                original_video_for_duration.close()
                voiceover_track = AudioFileClip(duration=video_duration)
            else:
                # 4. Combine TTS audio segments into a single voiceover track
                original_video_for_duration = VideoFileClip(input_video)
                video_duration = original_video_for_duration.duration
                original_video_for_duration.close()

                voiceover_track = create_composite_voiceover(
                    tts_clips_info, video_duration
                )

            # 5. Create final video
            create_final_video(input_video, voiceover_track, output_video)

        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)

    print(f"Processing finished. Output video: {output_video}")
