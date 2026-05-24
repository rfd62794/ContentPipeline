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

# Add content-engine to PATH for FFmpeg (required by Whisper)
content_engine_path = str(Path(__file__).parent)
if os.path.exists(content_engine_path):
    os.environ["PATH"] = content_engine_path + os.pathsep + os.environ.get("PATH", "")

from review_session import format_timestamp, transcribe
from stream_launcher import load_game_registry, is_game_running, get_active_window_title, is_game_focused, launch_game
from core.obs_manager import (
    OBSManager, OBSBoot, OBSCapture, OBSScenes, OBSSources,
    build_obs_recording_path, format_recording_note
)

TEMP_WAV = os.path.join("sessions", ".tmp_live_recording.wav")


def normalize_game_name(name: str) -> str:
    """Normalize game name for fuzzy matching: lowercase, remove spaces/special chars."""
    import re
    # Remove .exe extension if present
    name = name.replace(".exe", "")
    # Convert to lowercase
    name = name.lower()
    # Remove spaces and special characters, keep alphanumeric only
    name = re.sub(r'[^a-z0-9]', '', name)
    return name


def get_process_name_for_game(game_name: str, registry: dict) -> Optional[str]:
    """Get process name from registry for the given game name with fuzzy matching."""
    normalized_input = normalize_game_name(game_name)
    
    # Search registry for matching game name
    for appid_str, entry in registry.items():
        exe_name = entry.get("exe_name", "")
        window_title = entry.get("window_title", "")
        
        # Try exact match first (case-insensitive)
        if game_name.lower() in exe_name.lower() or game_name.lower() in window_title.lower():
            return exe_name
        
        # Try fuzzy match using normalized names
        normalized_exe = normalize_game_name(exe_name)
        normalized_window = normalize_game_name(window_title)
        
        if normalized_input in normalized_exe or normalized_input in normalized_window:
            return exe_name
    
    return None


def get_appid_for_game(game_name: str, registry: dict) -> Optional[int]:
    """Get Steam appid from registry for the given game name with fuzzy matching."""
    normalized_input = normalize_game_name(game_name)
    
    for appid_str, entry in registry.items():
        exe_name = entry.get("exe_name", "")
        window_title = entry.get("window_title", "")
        
        # Try exact match first (case-insensitive)
        if game_name.lower() in exe_name.lower() or game_name.lower() in window_title.lower():
            return int(appid_str)
        
        # Try fuzzy match using normalized names
        normalized_exe = normalize_game_name(exe_name)
        normalized_window = normalize_game_name(window_title)
        
        if normalized_input in normalized_exe or normalized_input in normalized_window:
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
    
    try:
        sys.stdout.write("Recording. Talk naturally. Ctrl+C or close game to stop.\n")
        sys.stdout.flush()
    except OSError:
        pass
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
        try:
            sys.stdout.write(f"Monitor started for {self.game_name}\n")
            sys.stdout.flush()
        except OSError:
            pass
        
        while not self.stop_event.is_set():
            try:
                # Check if game is still running
                if not is_game_running(self.process_name):
                    try:
                        sys.stdout.write(f"Game closed — stopping session\n")
                        sys.stdout.flush()
                    except OSError:
                        pass
                    self.game_closed = True
                    self.stop_event.set()
                    break
                
                # Check window focus
                window_title = get_active_window_title()
                is_focused = is_game_focused(window_title, self.game_name)
                
                # Focus lost → log pause
                if self.was_focused and not is_focused:
                    try:
                        sys.stdout.write("[paused — game not focused]\n")
                        sys.stdout.flush()
                    except OSError:
                        pass
                    self.was_focused = False
                
                # Focus returned → log resume
                elif not self.was_focused and is_focused:
                    try:
                        sys.stdout.write("[resumed]\n")
                        sys.stdout.flush()
                    except OSError:
                        pass
                    self.was_focused = True
                
                # Sleep for 3 seconds before next check
                time.sleep(3)
                
            except Exception as e:
                try:
                    sys.stdout.write(f"Monitor error: {e}\n")
                    sys.stdout.flush()
                except OSError:
                    pass
                time.sleep(3)
        
        try:
            sys.stdout.write("Monitor stopped\n")
            sys.stdout.flush()
        except OSError:
            pass
    
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
    parser.add_argument("--record", action="store_true", help="Enable OBS video recording")
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
    
    # Setup OBS recording if --record flag
    obs_manager = None
    recording_path = None
    if args.record:
        try:
            sys.stdout.write("Initializing OBS recording...\n")
            sys.stdout.flush()
        except OSError:
            pass
        
        obs_manager = OBSManager()
        if not OBSBoot.ensure_obs_running():
            try:
                sys.stdout.write("Failed to ensure OBS is running\n")
                sys.stdout.flush()
            except OSError:
                pass
            sys.exit(1)
        
        if not obs_manager.connect():
            try:
                sys.stdout.write("Failed to connect to OBS\n")
                sys.stdout.flush()
            except OSError:
                pass
            sys.exit(1)
        
        capture = OBSCapture(obs_manager)
        if not capture.start_recording():
            try:
                sys.stdout.write("Failed to start OBS recording\n")
                sys.stdout.flush()
            except OSError:
                pass
            sys.exit(1)
        
        recording_path = build_obs_recording_path(args.game, now)
        try:
            sys.stdout.write(f"OBS recording started: {recording_path}\n")
            sys.stdout.flush()
        except OSError:
            pass
    
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
        
        # Stop OBS recording if active
        if obs_manager and args.record:
            try:
                sys.stdout.write("Stopping OBS recording...\n")
                sys.stdout.flush()
            except OSError:
                pass
            
            obs_recording_path = capture.stop_recording()
            if obs_recording_path:
                try:
                    sys.stdout.write(f"OBS recording saved: {obs_recording_path}\n")
                    sys.stdout.flush()
                except OSError:
                    pass
            else:
                try:
                    sys.stdout.write("No OBS recording to save\n")
                    sys.stdout.flush()
                except OSError:
                    pass
            
            obs_manager.disconnect()
        
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
                
                # Add OBS recording note if applicable
                if args.record and recording_path:
                    recording_note = format_recording_note(recording_path, now)
                    header = f"{header}\n{recording_note}"
                
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