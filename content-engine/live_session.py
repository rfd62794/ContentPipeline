#!/usr/bin/env python3
"""
ContentPipeline Live Session Tool

Standalone CLI tool for recording live gameplay commentary.
Records audio while you play, transcribes with Whisper, and outputs a session file.
Auto-stops when game closes. Logs focus loss events without stopping recording.
"""

import argparse
import datetime
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from review_session import format_timestamp, transcribe
from stream_launcher import load_game_registry, is_game_running, get_active_window_title, is_game_focused, launch_game

TEMP_WAV = os.path.join("sessions", ".tmp_live_recording.wav")


def get_process_name_for_game(game_name: str, registry: dict) -> Optional[str]:
    """Get process name from registry for the given game name."""
    # Search registry for matching game name
    for appid_str, entry in registry.items():
        # Check if exe_name or window_title contains game name
        exe_name = entry.get("exe_name", "")
        window_title = entry.get("window_title", "")
        if game_name.lower() in exe_name.lower() or game_name.lower() in window_title.lower():
            return exe_name
    return None


def get_appid_for_game(game_name: str, registry: dict) -> Optional[int]:
    """Get Steam appid from registry for the given game name."""
    for appid_str, entry in registry.items():
        exe_name = entry.get("exe_name", "")
        window_title = entry.get("window_title", "")
        if game_name.lower() in exe_name.lower() or game_name.lower() in window_title.lower():
            return int(appid_str)
    return None


def build_session_header(game: str, date: datetime.datetime, duration: str, model: str) -> str:
    """Return formatted header block for live session."""
    date_str = date.strftime("%Y-%m-%d %H:%M:%S")
    
    header = f"""# Live Session
# Game: {game}
# Date: {date_str}
# Duration: {duration}
# Model: {model}"""
    return header


def build_live_transcript(header: str, segments: list) -> str:
    """Assemble final file string. Header + blank line + one [timestamp] line per segment."""
    lines = [header, ""]
    for segment in segments:
        timestamp = format_timestamp(segment["start"])
        text = segment["text"].strip()
        lines.append(f"[{timestamp}] {text}")
    return "\n".join(lines)


def record_audio(output_path: str, stop_event: threading.Event, samplerate: int = 16000) -> None:
    """Open sounddevice InputStream. Block on input(). Write WAV to output_path on stop.
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
    
    print("Recording. Talk naturally. Ctrl+C or close game to stop.")
    # Start recording
    with sd.InputStream(samplerate=samplerate, channels=1, dtype=np.float32, callback=callback):
        # Record until stop event is set
        while not stop_event.is_set():
            time.sleep(0.1)
    
    # Convert frames to numpy array and save
    if not audio_frames:
        raise ValueError("No audio frames recorded")
    audio_data = np.concatenate(audio_frames, axis=0)
    wav.write(output_path, samplerate, audio_data)


class LiveSessionMonitor:
    """Background thread for monitoring game process and focus status."""
    
    def __init__(self, process_name: str, game_name: str, stop_event: threading.Event):
        self.process_name = process_name
        self.game_name = game_name
        self.stop_event = stop_event
        self.was_focused = True
        self.game_closed = False
    
    def run(self):
        """Main monitoring loop. Runs in daemon thread."""
        print(f"Monitor started for {self.game_name}")
        
        while not self.stop_event.is_set():
            try:
                # Check if game is still running
                if not is_game_running(self.process_name):
                    print(f"Game closed — stopping session")
                    self.game_closed = True
                    self.stop_event.set()
                    break
                
                # Check window focus
                window_title = get_active_window_title()
                is_focused = is_game_focused(window_title, self.game_name)
                
                # Focus lost → log pause
                if self.was_focused and not is_focused:
                    print("[paused — game not focused]")
                    self.was_focused = False
                
                # Focus returned → log resume
                elif not self.was_focused and is_focused:
                    print("[resumed]")
                    self.was_focused = True
                
                # Sleep for 3 seconds before next check
                time.sleep(3)
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(3)
        
        print("Monitor stopped")
    
    def is_game_closed(self) -> bool:
        """Check if game was detected as closed."""
        return self.game_closed


def main() -> None:
    """Full orchestration sequence. Wrap critical section in try/finally.
    finally block: stop recording if active, delete temp WAV."""
    parser = argparse.ArgumentParser(description="ContentPipeline Live Session Tool")
    parser.add_argument("--game", required=True, help="Game name (must match registry entry)")
    parser.add_argument("--output-dir", default="sessions", dest="output_dir")
    parser.add_argument("--model", default="base")
    args = parser.parse_args()
    
    # Load game registry
    registry = load_game_registry()
    if not registry:
        print("Error: Game registry is empty. Run stream_launcher.py first to populate registry.", file=sys.stderr)
        sys.exit(1)
    
    # Get process name and appid for game
    process_name = get_process_name_for_game(args.game, registry)
    appid = get_appid_for_game(args.game, registry)
    
    if not process_name:
        print(f"Error: Game '{args.game}' not found in registry. Available games: {list(registry.keys())}", file=sys.stderr)
        sys.exit(1)
    
    if not appid:
        print(f"Error: Could not find appid for '{args.game}'", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found process name for {args.game}: {process_name}")
    print(f"Found appid for {args.game}: {appid}")
    
    # Verify game is running, launch if not
    if not is_game_running(process_name):
        print(f"Game is not running. Launching {args.game}...")
        launch_game(appid)
        print("Waiting for game to start...")
        
        # Wait for game to start (up to 30 seconds)
        import time as time_module
        for i in range(30):
            time_module.sleep(1)
            if is_game_running(process_name):
                print(f"Game started after {i+1} seconds")
                break
        else:
            print(f"Error: Game did not start within 30 seconds", file=sys.stderr)
            sys.exit(1)
    
    print(f"Game is running: {process_name}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Build session file path
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    session_filename = f"{args.game}_live_{timestamp}.txt"
    session_path = os.path.join(args.output_dir, session_filename)
    
    # Setup monitoring
    stop_event = threading.Event()
    monitor = LiveSessionMonitor(process_name, args.game, stop_event)
    monitor_thread = threading.Thread(target=monitor.run, daemon=True)
    
    recording_active = False
    
    try:
        # Start monitoring thread
        monitor_thread.start()
        
        # Start recording
        recording_active = True
        record_audio(TEMP_WAV, stop_event)
        recording_active = False
        
    except KeyboardInterrupt:
        print("\nRecording stopped by user")
        stop_event.set()
        
    finally:
        # Stop monitoring
        stop_event.set()
        if monitor_thread.is_alive():
            monitor_thread.join(timeout=2)
        
        # Transcribe if recording completed (game close is normal stop)
        if os.path.exists(TEMP_WAV):
            print("Transcribing audio...")
            try:
                segments = transcribe(TEMP_WAV, args.model)
                
                # Calculate duration
                if segments:
                    duration = segments[-1]["end"]
                    duration_str = format_timestamp(duration)
                else:
                    duration_str = "00:00"
                
                # Build session file
                session_dt = datetime.datetime.now()
                header = build_session_header(args.game, session_dt, duration_str, args.model)
                transcript = build_live_transcript(header, segments)
                
                # Write session file
                with open(session_path, 'w', encoding='utf-8') as f:
                    f.write(transcript)
                
                print(f"Session saved to: {session_path}")
                
            except Exception as e:
                print(f"Error during transcription: {e}", file=sys.stderr)
        else:
            print("Recording incomplete — session not saved")
        
        # Cleanup temp file (regardless of how session ends)
        if os.path.exists(TEMP_WAV):
            try:
                os.remove(TEMP_WAV)
                print(f"Cleaned up temp file: {TEMP_WAV}")
            except Exception as e:
                print(f"Error removing temp file: {e}")


if __name__ == "__main__":
    main()