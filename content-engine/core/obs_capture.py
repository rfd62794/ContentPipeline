"""
OBS WebSocket capture module for automated game recording.

This module provides a Python interface to OBS Studio via the WebSocket API,
enabling automated scene switching, recording control, and file path retrieval.

Contract:
- connect(host='localhost', port=4455, password=''): Establish connection to OBS
- start_recording(): Start recording, returns None
- stop_recording(): Stop recording, returns file path of recorded video
- get_status(): Get recording status (active, bytes, duration)
- set_scene(scene_name): Switch to specified scene
- disconnect(): Close WebSocket connection

Dependencies:
- obsws_python v1.8.0 (installed via UV)
- OBS Studio with WebSocket enabled on localhost:4455
"""

import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import obsws_python as obs
except ImportError:
    obs = None


@dataclass
class RecordingStatus:
    """Status of OBS recording."""
    active: bool
    bytes_written: int
    duration_seconds: float
    timecode: str


class OBSCaptureError(Exception):
    """Exception raised for OBS capture errors."""
    pass


class OBSCapture:
    """
    OBS WebSocket client for automated recording.
    
    Provides interface to OBS Studio recording control via WebSocket API.
    """

    def __init__(self, host: str = 'localhost', port: int = 4455, password: str = ''):
        """
        Initialize OBS WebSocket client.
        
        Args:
            host: OBS WebSocket host address
            port: OBS WebSocket port
            password: OBS WebSocket password (empty string if no password)
        """
        if obs is None:
            raise OBSCaptureError("obsws_python not installed. Install with: uv add obsws-python")
        
        self.host = host
        self.port = port
        self.password = password
        self.client: Optional[obs.ReqClient] = None
        self.connected = False

    def connect(self) -> None:
        """
        Establish connection to OBS WebSocket.
        
        Raises:
            OBSCaptureError: If connection fails
        """
        try:
            self.client = obs.ReqClient(
                host=self.host,
                port=self.port,
                password=self.password,
                timeout=5
            )
            self.connected = True
        except Exception as e:
            raise OBSCaptureError(f"Failed to connect to OBS: {e}")

    def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self.client:
            # obsws_python doesn't have explicit disconnect, rely on garbage collection
            self.client = None
            self.connected = False

    def start_recording(self) -> None:
        """
        Start OBS recording.
        
        Raises:
            OBSCaptureError: If recording fails to start or already active
        """
        if not self.connected:
            raise OBSCaptureError("Not connected to OBS")
        
        try:
            self.client.start_record()
        except obs.error.OBSSDKRequestError as e:
            if "500" in str(e):
                # Error 500 typically means recording already active
                raise OBSCaptureError("Recording already active")
            raise OBSCaptureError(f"Failed to start recording: {e}")

    def stop_recording(self) -> str:
        """
        Stop OBS recording and return file path.
        
        Returns:
            File path of the recorded video
            
        Raises:
            OBSCaptureError: If recording fails to stop or not active
        """
        if not self.connected:
            raise OBSCaptureError("Not connected to OBS")
        
        # Capture file path before stopping
        try:
            settings = self.client.get_output_settings('simple_file_output')
            file_path = settings.output_settings['path']
        except Exception as e:
            raise OBSCaptureError(f"Failed to get output settings: {e}")
        
        # Stop recording
        try:
            self.client.stop_record()
        except obs.error.OBSSDKRequestError as e:
            if "500" in str(e):
                # Error 500 typically means no recording active
                raise OBSCaptureError("No recording active")
            raise OBSCaptureError(f"Failed to stop recording: {e}")
        
        return file_path

    def get_status(self) -> RecordingStatus:
        """
        Get current recording status.
        
        Returns:
            RecordingStatus object with current recording state
            
        Raises:
            OBSCaptureError: If status check fails
        """
        if not self.connected:
            raise OBSCaptureError("Not connected to OBS")
        
        try:
            status = self.client.get_record_status()
            return RecordingStatus(
                active=status.output_active,
                bytes_written=status.output_bytes,
                duration_seconds=status.output_duration,
                timecode=status.output_timecode
            )
        except Exception as e:
            raise OBSCaptureError(f"Failed to get recording status: {e}")

    def set_scene(self, scene_name: str) -> None:
        """
        Switch to specified scene.
        
        Args:
            scene_name: Name of scene to switch to
            
        Raises:
            OBSCaptureError: If scene switch fails
        """
        if not self.connected:
            raise OBSCaptureError("Not connected to OBS")
        
        try:
            self.client.set_current_program_scene(scene_name)
        except Exception as e:
            raise OBSCaptureError(f"Failed to set scene: {e}")

    def list_scenes(self) -> list[str]:
        """
        Get list of available scenes.
        
        Returns:
            List of scene names
            
        Raises:
            OBSCaptureError: If scene list retrieval fails
        """
        if not self.connected:
            raise OBSCaptureError("Not connected to OBS")
        
        try:
            scenes = self.client.get_scene_list()
            return [scene.scene_name for scene in scenes.scenes]
        except Exception as e:
            raise OBSCaptureError(f"Failed to get scene list: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Convenience function for quick recording
def quick_record(duration_seconds: float, host: str = 'localhost', port: int = 4455) -> str:
    """
    Quick recording helper - start, record for duration, stop, return file path.
    
    Args:
        duration_seconds: Recording duration in seconds
        host: OBS WebSocket host
        port: OBS WebSocket port
        
    Returns:
        File path of recorded video
    """
    with OBSCapture(host=host, port=port) as obs_cap:
        obs_cap.start_recording()
        time.sleep(duration_seconds)
        return obs_cap.stop_recording()
