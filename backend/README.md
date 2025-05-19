# Shiki Voiceover

A Python tool that takes a video file, creates an SRT subtitle file, and then generates an AI voiceover using ElevenLabs. The script maintains the original timing of the subtitles when creating the voiceover.

## Features

- Extracts audio from video files
- Transcribes audio to text with precise timestamps using OpenAI's Whisper
- Generates high-quality text-to-speech using ElevenLabs
- Creates a new video with AI voiceover
- Optional SRT file export
- Command-line interface with multiple options

## Requirements

- Python 3.8+
- FFmpeg installed and in your PATH
- ElevenLabs API key

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
5. Create a `.env` file in the root directory with your ElevenLabs API key:
   ```
   ELEVENLABS_API_KEY=your_key_here
   ```

## Usage

Basic usage:

```bash
python video_voiceover.py input_video.mp4
```

Advanced options:

```bash
python video_voiceover.py input_video.mp4 -o output_video.mp4 -m medium -l en -v "ElevenLabs_Voice_ID" -s
```

List available ElevenLabs voices:

```bash
python video_voiceover.py --list-voices
```

### Command-line Options

- `input_video`: Path to the input video file
- `-o, --output`: Path to the output video file (default: "output_with_voiceover.mp4")
- `-m, --model`: Whisper model size (choices: "tiny", "base", "small", "medium", "large", default: "base")
- `-l, --language`: Language code (e.g., 'en' for English)
- `-v, --voice-id`: ElevenLabs voice ID
- `-s, --srt`: Save SRT file
- `--list-voices`: List available ElevenLabs voices

## Performance Notes

- The "tiny" and "base" Whisper models are faster but less accurate
- The "small", "medium", and "large" models are more accurate but slower and require more memory
- For short videos, the "base" model is usually sufficient
- For longer or more complex videos, consider using the "medium" model
- The "large" model provides the best quality but requires significant computational resources

## License

MIT

## Credits

This tool uses:
- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [ElevenLabs](https://elevenlabs.io/) for text-to-speech
- [MoviePy](https://zulko.github.io/moviepy/) for video processing 