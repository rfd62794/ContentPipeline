"""
OBS Manager — Single interface for OBS Studio control.

Provides unified interface to OBS Studio via WebSocket API using obsws_python.
Combines recording, streaming, scene switching, and source management.

Contract:
- connect() -> bool: Establish connection to OBS
- disconnect() -> None: Close WebSocket connection
- ensure_obs_running(exe_path) -> bool: Launch OBS if not running
- is_connected() -> bool: Check connection status

Scenes:
- switch_scene(scene_name) -> bool: Switch to specified scene
- list_scenes() -> list[str]: Get list of available scenes

Recording:
- start_recording() -> bool: Start recording
- stop_recording() -> Optional[str]: Stop recording, return file path
- pause_recording() -> bool: Pause recording
- resume_recording() -> bool: Resume recording
- is_recording() -> bool: Check recording status

Streaming:
- start_stream() -> bool: Start streaming output
- stop_stream() -> bool: Stop streaming output
- get_stream_stats() -> dict: Get streaming statistics

Sources:
- add_game_capture(scene_name, window_title, source_name) -> bool: Add game capture source
- remove_game_capture(scene_name, source_name) -> bool: Remove game capture source
- mute_source(source_name) -> bool: Mute audio source
- unmute_source(source_name) -> bool: Unmute audio source

All methods return False/None on failure, never raise.
Uses logging for errors, not print().
Uses obsws_python exclusively.

Dependencies:
- obsws_python v1.8.0
- OBS Studio with WebSocket enabled on localhost:4455
"""

import logging
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None

try:
    import obsws_python as obs
except ImportError:
    obs = None

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RecordingStatus:
    """Status of OBS recording."""
    active: bool
    bytes_written: int
    duration_seconds: float
    timecode: str


@dataclass
class StreamStats:
    """Streaming statistics."""
    bitrate: int
    dropped_frames: int
    total_frames: int
    duration_seconds: float


class OBSManager:
    """
    Unified OBS Manager for recording, streaming, and source control.
    
    Instance-based connection management with context manager support.
    All methods return False/None on failure, never raise exceptions.
    """

    def __init__(self, host: str = 'localhost', port: int = 4455, password: str = ''):
        """
        Initialize OBS Manager.
        
        Args:
            host: OBS WebSocket host address
            port: OBS WebSocket port
            password: OBS WebSocket password (empty string if no password)
        """
        if obs is None:
            logger.error("obsws_python not installed. Install with: uv add obsws-python")
            self._available = False
        else:
            self._available = True
        
        self.host = host
        self.port = port
        self.password = password
        self.client: Optional[obs.ReqClient] = None
        self.connected = False

    def connect(self) -> bool:
        """
        Establish connection to OBS WebSocket.
        
        Returns:
            True on success, False on failure
        """
        if not self._available:
            logger.error("obsws_python not available")
            return False
        
        try:
            self.client = obs.ReqClient(
                host=self.host,
                port=self.port,
                password=self.password,
                timeout=5
            )
            self.connected = True
            logger.info(f"Connected to OBS at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OBS: {e}")
            return False

    def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self.client:
            self.client = None
            self.connected = False
            logger.info("Disconnected from OBS")

    def is_connected(self) -> bool:
        """Check if connected to OBS."""
        return self.connected

    def ensure_obs_running(self, obs_exe_path: Optional[str] = None) -> bool:
        """
        Check if OBS is running. If not, launch it and wait up to 10 seconds.
        
        Args:
            obs_exe_path: Override path to OBS64.exe. If None, checks common paths.
        
        Returns:
            True if OBS is ready, False if launch failed or timed out.
        """
        if psutil is None:
            logger.error("psutil not available, cannot check OBS status")
            return False
        
        # Check if OBS is already running
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'obs' in proc.info['name'].lower():
                logger.info("OBS is already running")
                return True
        
        # Find OBS executable
        if obs_exe_path:
            exe_path = Path(obs_exe_path)
        else:
            common_paths = [
                "C:/Program Files/obs-studio/bin/64bit/obs64.exe",
                "C:/Program Files (x86)/obs-studio/bin/64bit/obs64.exe",
            ]
            for path in common_paths:
                if Path(path).exists():
                    exe_path = Path(path)
                    break
            else:
                logger.error("OBS executable not found in common paths")
                return False
        
        # Launch OBS from its installation directory to find locale files
        logger.info(f"Launching OBS from {exe_path}")
        try:
            subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent), shell=True)
        except Exception as e:
            logger.error(f"Error launching OBS: {e}")
            return False
        
        # Wait for OBS to start (up to 10 seconds)
        for i in range(10):
            time.sleep(1)
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and 'obs' in proc.info['name'].lower():
                    logger.info(f"OBS detected after {i+1} seconds")
                    # Give WebSocket server additional time to initialize
                    logger.info("Waiting for WebSocket server to initialize...")
                    time.sleep(3)
                    return True
        
        logger.error("OBS did not start within 10 seconds")
        return False

    def switch_scene(self, scene_name: str) -> bool:
        """
        Switch OBS to named scene.
        
        Args:
            scene_name: Name of scene to switch to
        
        Returns:
            True on success, False on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False
        
        try:
            self.client.set_current_program_scene(scene_name)
            logger.info(f"Switched OBS to scene: {scene_name}")
            return True
        except Exception as e:
            logger.error(f"Error switching OBS scene: {e}")
            return False

    def list_scenes(self) -> List[str]:
        """
        Get list of available scenes.
        
        Returns:
            List of scene names, empty list on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return []
        
        try:
            scenes = self.client.get_scene_list()
            return [scene.scene_name for scene in scenes.scenes]
        except Exception as e:
            logger.error(f"Error getting scene list: {e}")
            return []

    def start_recording(self) -> bool:
        """
        Start OBS recording.
        
        Returns:
            True on success, False on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False
        
        try:
            self.client.start_record()
            logger.info("Started OBS recording")
            return True
        except obs.error.OBSSDKRequestError as e:
            if "500" in str(e):
                logger.error("Recording already active")
            else:
                logger.error(f"Failed to start recording: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False

    def stop_recording(self) -> Optional[str]:
        """
        Stop OBS recording and return file path.
        
        Returns:
            File path of recorded video, None on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return None
        
        # Capture file path before stopping
        try:
            settings = self.client.get_output_settings('simple_file_output')
            file_path = settings.output_settings['path']
        except Exception as e:
            logger.error(f"Failed to get output settings: {e}")
            return None
        
        # Stop recording
        try:
            self.client.stop_record()
            logger.info(f"Stopped OBS recording: {file_path}")
            return file_path
        except obs.error.OBSSDKRequestError as e:
            if "500" in str(e):
                logger.error("No recording active")
            else:
                logger.error(f"Failed to stop recording: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return None

    def pause_recording(self) -> bool:
        """
        Pause OBS recording.
        
        Returns:
            True on success, False on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False

        try:
            self.client.pause_record()
            logger.info("Paused OBS recording")
            return True
        except obs.error.OBSSDKRequestError as e:
            if "500" in str(e):
                logger.error("No recording active")
            else:
                logger.error(f"Failed to pause recording: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to pause recording: {e}")
            return False

    def resume_recording(self) -> bool:
        """
        Resume OBS recording.
        
        Returns:
            True on success, False on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False

        try:
            self.client.resume_record()
            logger.info("Resumed OBS recording")
            return True
        except obs.error.OBSSDKRequestError as e:
            if "500" in str(e):
                logger.error("Recording not paused")
            else:
                logger.error(f"Failed to resume recording: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to resume recording: {e}")
            return False

    def is_recording(self) -> bool:
        """
        Check if recording is active.
        
        Returns:
            True if recording, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            status = self.client.get_record_status()
            return status.output_active
        except Exception as e:
            logger.error(f"Failed to get recording status: {e}")
            return False

    def get_recording_status(self) -> Optional[RecordingStatus]:
        """
        Get current recording status.
        
        Returns:
            RecordingStatus object, None on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return None
        
        try:
            status = self.client.get_record_status()
            return RecordingStatus(
                active=status.output_active,
                bytes_written=status.output_bytes,
                duration_seconds=status.output_duration,
                timecode=status.output_timecode
            )
        except Exception as e:
            logger.error(f"Failed to get recording status: {e}")
            return None

    def start_stream(self) -> bool:
        """
        Start OBS streaming output.
        
        Returns:
            True on success, False on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False
        
        try:
            self.client.start_stream()
            logger.info("Started OBS streaming")
            return True
        except Exception as e:
            logger.error(f"Error starting OBS stream: {e}")
            return False

    def stop_stream(self) -> bool:
        """
        Stop OBS streaming output.
        
        Returns:
            True on success, False on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False
        
        try:
            self.client.stop_stream()
            logger.info("Stopped OBS streaming")
            return True
        except Exception as e:
            logger.error(f"Error stopping OBS stream: {e}")
            return False

    def get_stream_stats(self) -> Optional[StreamStats]:
        """
        Get streaming statistics.
        
        Returns:
            StreamStats object, None on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return None
        
        try:
            stats = self.client.get_stream_status()
            return StreamStats(
                bitrate=stats.output_bitrate,
                dropped_frames=stats.output_dropped_frames,
                total_frames=stats.output_total_frames,
                duration_seconds=stats.output_duration
            )
        except Exception as e:
            logger.error(f"Failed to get stream stats: {e}")
            return None

    def add_game_capture(self, scene_name: str, window_title: str, source_name: str = "Game Capture") -> bool:
        """
        Add Game Capture source to named scene.
        Captures specific window matching window_title.
        Positions full screen (1920x1080, x=0, y=0).
        
        Args:
            scene_name: Scene to add source to
            window_title: Window title to capture
            source_name: Name for the source (default "Game Capture")
        
        Returns:
            True on success, False on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False
        
        try:
            logger.info(f"Adding game capture to scene: {scene_name}")
            logger.info(f"Target window: {window_title}")
            logger.info(f"Source name: {source_name}")
            
            # Remove existing source if it exists
            scene_items = self.client.get_scene_list()
            for scene in scene_items.scenes:
                if scene.scene_name == scene_name:
                    # Get scene items
                    items = self.client.get_scene_item_list(scene_name)
                    for item in items.scene_items:
                        if item.source_name == source_name:
                            logger.info(f"Removing existing {source_name} from {scene_name}")
                            self.client.remove_scene_item(scene_name, item.scene_item_id)
                            break
                    break
            
            # Create the Game Capture source
            self.client.create_input(
                scene_name=scene_name,
                input_name=source_name,
                input_kind='game_capture',
                scene_item_enabled=True
            )
            logger.info(f"Created {source_name} in {scene_name}")
            
            # Set source settings to capture specific window
            self.client.set_input_settings(
                input_name=source_name,
                input_settings={
                    'capture_mode': 'window',
                    'window': window_title,
                    'allow_transparency': False
                }
            )
            logger.info(f"Set {source_name} to capture window: {window_title}")
            
            # Position full screen
            items = self.client.get_scene_item_list(scene_name)
            for item in items.scene_items:
                if item.source_name == source_name:
                    self.client.set_scene_item_transform(
                        scene_name=scene_name,
                        scene_item_id=item.scene_item_id,
                        scene_item_transform={
                            'positionX': 0,
                            'positionY': 0,
                            'scaleX': 1.0,
                            'scaleY': 1.0
                        }
                    )
                    logger.info(f"Positioned {source_name} at (0, 0) with scale 1.0")
                    break
            
            logger.info(f"SUCCESS: Game Capture source configured")
            return True
            
        except Exception as e:
            logger.error(f"Error adding game capture source: {e}")
            return False

    def remove_game_capture(self, scene_name: str, source_name: str = "Game Capture") -> bool:
        """
        Remove Game Capture source from scene.
        
        Args:
            scene_name: Scene to remove source from
            source_name: Name of source to remove
        
        Returns:
            True if removed, False if not found or error
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False
        
        try:
            items = self.client.get_scene_item_list(scene_name)
            for item in items.scene_items:
                if item.source_name == source_name:
                    self.client.remove_scene_item(scene_name, item.scene_item_id)
                    logger.info(f"Removed {source_name} from {scene_name}")
                    return True
            
            logger.info(f"{source_name} not found in {scene_name}")
            return False
        except Exception as e:
            logger.error(f"Error removing game capture source: {e}")
            return False

    def mute_source(self, source_name: str) -> bool:
        """
        Mute audio source.
        
        Args:
            source_name: Name of source to mute
        
        Returns:
            True on success, False on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False
        
        try:
            self.client.set_input_mute(input_name=source_name, input_muted=True)
            logger.info(f"Muted source: {source_name}")
            return True
        except Exception as e:
            logger.error(f"Error muting source: {e}")
            return False

    def unmute_source(self, source_name: str) -> bool:
        """
        Unmute audio source.
        
        Args:
            source_name: Name of source to unmute
        
        Returns:
            True on success, False on failure
        """
        if not self.connected:
            logger.error("Not connected to OBS")
            return False
        
        try:
            self.client.set_input_mute(input_name=source_name, input_muted=False)
            logger.info(f"Unmuted source: {source_name}")
            return True
        except Exception as e:
            logger.error(f"Error unmuting source: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Pure functions for path building and formatting

def build_obs_recording_path(game_name: str, dt: datetime) -> str:
    """
    Build OBS recording file path.
    
    Args:
        game_name: Name of the game
        dt: DateTime for timestamp
    
    Returns:
        Formatted recording path
    """
    timestamp = dt.strftime("%Y%m%d_%H%M%S")
    return f"{game_name}_{timestamp}.mp4"


def format_recording_note(path: str, dt: datetime) -> str:
    """
    Format recording note for session header.
    
    Args:
        path: Recording file path
        dt: DateTime of recording
    
    Returns:
        Formatted note string
    """
    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
    return f"# OBS Recording: {path} at {timestamp}"


def parse_stream_stats(raw_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse raw OBS stream stats response.
    
    Args:
        raw_response: Raw response from OBS
    
    Returns:
        Parsed stats dictionary
    """
    return {
        'bitrate': raw_response.get('output_bitrate', 0),
        'dropped_frames': raw_response.get('output_dropped_frames', 0),
        'total_frames': raw_response.get('output_total_frames', 0),
        'duration': raw_response.get('output_duration', 0)
    }
