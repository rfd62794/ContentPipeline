#!/usr/bin/env python3
"""
ContentPipeline Review Session Tool

Standalone CLI tool for recording time-aligned spoken annotations over existing video footage.
The director watches a video in VLC and talks aloud — reactions, builder observations, content ideas.
The tool captures audio simultaneously, transcribes it with Whisper, and outputs a session file
where every timestamp maps directly to video position, not audio position.

This is a capture tool, not a pipeline stage. It does not write to content_engine.db.
It does not call OpenRouter. It produces flat text files in sessions/ that the director reads
and mines for script angles, devlog content, and YouTube Shorts ideas.
"""

import argparse
import datetime
import os
import subprocess
import sys
import tempfile
import time


TEMP_WAV = os.path.join("sessions", ".tmp_recording.wav")


def format_timestamp(seconds: float) -> str:
    """Convert float seconds to [HH:]MM:SS string. 242.0 → '04:02'. 3661.5 → '01:01:01'."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def sanitize_slug(video_path: str) -> str:
    """Extract filename stem from path. Replace spaces and colons with underscores."""
    filename = os.path.basename(video_path)
    stem = os.path.splitext(filename)[0]
    # Replace spaces and colons with underscores
    slug = stem.replace(" ", "_").replace(":", "_")
    return slug


def build_session_path(output_dir: str, slug: str, start_time: int) -> str:
    """Return full session file path.
    Format: <output_dir>/<slug>_offset<N>s_<YYYYMMDD>_<HHMMSS>.txt
    Uses datetime.datetime.now() internally."""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{slug}_offset{start_time}s_{timestamp}.txt"
    return os.path.join(output_dir, filename)


def offset_segments(segments: list, offset: int) -> list:
    """Return new list of dicts with segment['start'] += offset for all items.
    Does not mutate input list."""
    offset_list = []
    for segment in segments:
        new_segment = segment.copy()
        new_segment["start"] += offset
        offset_list.append(new_segment)
    return offset_list


def build_header(video_path: str, start_time: int, model: str, session_dt: datetime.datetime, segment_count: int, audio_duration: str) -> str:
    """Return formatted header block string. See SDD §5 for exact format."""
    timestamp_str = format_timestamp(start_time)
    session_str = session_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    header = f"""# Review Session
# Video: {os.path.basename(video_path)}
# Source: {video_path}
# Video offset: {timestamp_str} ({start_time}s)
# Pass recorded: {session_str}
# Whisper model: {model}
# Segments: {segment_count}
# Audio duration: {audio_duration}"""
    return header


def build_transcript(header: str, segments: list) -> str:
    """Assemble final file string. Header + blank line + one [timestamp] line per segment."""
    lines = [header, ""]
    for segment in segments:
        timestamp = format_timestamp(segment["start"])
        text = segment["text"].strip()
        lines.append(f"[{timestamp}] {text}")
    return "\n".join(lines)


def resolve_vlc_path() -> str:
    """Return platform-correct VLC binary path.
    Windows: C:\\Program Files\\VideoLAN\\VLC\\vlc.exe
    Other: 'vlc' (assume on PATH)
    Raises FileNotFoundError if Windows path does not exist."""
    if sys.platform == "win32":
        vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
        if not os.path.exists(vlc_path):
            raise FileNotFoundError(f"VLC not found at {vlc_path}. Please install VLC Media Player.")
        return vlc_path
    else:
        return "vlc"


def record_audio(output_path: str, samplerate: int = 16000, duration: int = None) -> None:
    """Open sounddevice InputStream. Block on input() or duration. Write WAV to output_path on stop.
    Ctrl+C raises KeyboardInterrupt — let it propagate to main()."""
    import numpy as np
    import sounddevice as sd
    import scipy.io.wavfile as wav
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Recording callback
    audio_frames = []
    
    def callback(indata, frames, time, status):
        if status:
            print(f"Recording status: {status}", file=sys.stderr)
        audio_frames.append(indata.copy())
    
    if duration:
        print(f"Recording for {duration} seconds...")
        # Start recording with timer
        with sd.InputStream(samplerate=samplerate, channels=1, dtype=np.float32, callback=callback):
            sd.sleep(duration * 1000)  # Convert to milliseconds
    else:
        print("Recording... Press Enter to stop.")
        # Start recording
        with sd.InputStream(samplerate=samplerate, channels=1, dtype=np.float32, callback=callback):
            input()  # Block until Enter is pressed
    
    # Convert frames to numpy array and save
    audio_data = np.concatenate(audio_frames, axis=0)
    wav.write(output_path, samplerate, audio_data)



def launch_vlc(video_path: str, start_time: int, vlc_path: str) -> subprocess.Popen:
    """Launch VLC as subprocess. Args: --start-time, --no-loop, --quiet.
    Return the Popen handle. Do not block."""
    args = [
        vlc_path,
        video_path,
        f"--start-time={start_time}",
        "--no-loop",
        "--quiet",
        "--play-and-exit"
    ]
    process = subprocess.Popen(args)
    return process


def transcribe(wav_path: str, model_name: str) -> list:
    """Load whisper model. Transcribe wav_path. Return result['segments']."""
    import whisper
    
    model = whisper.load_model(model_name)
    result = model.transcribe(wav_path)
    return result["segments"]


def main() -> None:
    """Full orchestration sequence per SDD §3. Wrap critical section in try/finally.
    finally block: stop recording if active, terminate VLC if active, delete temp WAV."""
    parser = argparse.ArgumentParser(description="ContentPipeline Review Session Tool")
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument("--start-time", type=int, default=0, dest="start_time")
    parser.add_argument("--model", default="base")
    parser.add_argument("--output-dir", default="sessions", dest="output_dir")
    parser.add_argument("--duration", type=int, default=None, help="Recording duration in seconds (for automated testing)")
    args = parser.parse_args()
    
    # Validate video path exists
    if not os.path.exists(args.video_path):
        print(f"Error: Video file not found: {args.video_path}", file=sys.stderr)
        sys.exit(1)
    
    # Resolve VLC path
    try:
        vlc_path = resolve_vlc_path()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Build session file path
    slug = sanitize_slug(args.video_path)
    session_path = build_session_path(args.output_dir, slug, args.start_time)
    
    # Create output directory if needed
    os.makedirs(args.output_dir, exist_ok=True)
    
    vlc_process = None
    recording_active = False
    
    try:
        # Launch VLC
        vlc_process = launch_vlc(args.video_path, args.start_time, vlc_path)
        
        # Start recording
        recording_active = True
        record_audio(TEMP_WAV, duration=args.duration)
        recording_active = False
        
        # Transcribe
        segments = transcribe(TEMP_WAV, args.model)
        
        # Offset segments
        offset_segments_list = offset_segments(segments, args.start_time)
        
        # Calculate duration and segment count
        segment_count = len(segments)
        if segments:
            duration = segments[-1]["end"]
            duration_str = format_timestamp(duration)
        else:
            duration_str = "00:00"
        
        # Build header and transcript
        session_dt = datetime.datetime.now()
        header = build_header(args.video_path, args.start_time, args.model, session_dt, segment_count, duration_str)
        transcript = build_transcript(header, offset_segments_list)
        
        # Write session file
        with open(session_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        
        # Print summary
        print(f"\nSession saved: {session_path}")
        print(f"Segments: {segment_count}")
        print(f"Audio duration: {duration_str}")
        
    except KeyboardInterrupt:
        print("\nRecording stopped by user.", file=sys.stderr)
        # Continue to finally block for cleanup
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Delete temp WAV if it exists
        if os.path.exists(TEMP_WAV):
            try:
                os.remove(TEMP_WAV)
            except Exception as e:
                print(f"Warning: Could not delete temp WAV: {e}", file=sys.stderr)
        
        # Terminate VLC if still running
        if vlc_process is not None:
            try:
                vlc_process.terminate()
                vlc_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                vlc_process.kill()
            except Exception as e:
                print(f"Warning: VLC termination error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
