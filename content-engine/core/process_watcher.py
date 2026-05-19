"""
Process Watcher — Detect game process and trigger OBS recording

Contract:
- is_running(process_name) returns True if process is running
- watch(process_name, scene, poll_interval) blocks until process exits after being detected
- All OBS calls go through OBSCapture parameter
- Process name is never hardcoded — caller provides it
- Uses subprocess only (tasklist) — no external dependencies
"""

import subprocess
import time
import threading
from typing import Optional


class ProcessWatcher:
    """Watch for a game process and trigger OBS recording automatically."""
    
    def __init__(self, obs, logger) -> None:
        """
        Initialize ProcessWatcher.
        
        Args:
            obs: OBSCapture instance for recording control
            logger: Logger instance for state transition logging
        """
        self.obs = obs
        self.logger = logger
        self._stop_flag = threading.Event()
    
    def is_running(self, process_name: str) -> bool:
        """
        Check if a process is currently running.
        
        Args:
            process_name: Name of the process to check (e.g., "Everything is Crab.exe")
            
        Returns:
            True if process is found in tasklist output, False otherwise
            Returns False on any exception — never crash
        """
        try:
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {process_name}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Process is running if its name appears in output
            return process_name in result.stdout
        except Exception:
            # Never crash on subprocess errors
            return False
    
    def watch(self, process_name: str, scene: Optional[str] = None, poll_interval: int = 5) -> str:
        """
        Watch for process and trigger OBS recording.
        
        This is a blocking call. It does not return until the game process
        has been detected AND subsequently closed.
        
        State machine: WAITING → RECORDING → DONE
        
        Args:
            process_name: Name of the process to watch for
            scene: Optional OBS scene to switch to before recording
            poll_interval: Seconds between process checks (default: 5)
            
        Returns:
            File path of recorded video, or empty string if stopped manually
        """
        self._stop_flag.clear()
        state = "WAITING"
        
        self.logger.info(f"ProcessWatcher: Waiting for {process_name}...")
        
        try:
            while not self._stop_flag.is_set():
                if state == "WAITING":
                    # Check if process is running
                    if self.is_running(process_name):
                        self.logger.info(f"ProcessWatcher: Detected {process_name}")
                        
                        # Switch scene if provided
                        if scene:
                            self.obs.set_scene(scene)
                            self.logger.info(f"ProcessWatcher: Switched to scene: {scene}")
                        
                        # Start recording
                        self.obs.start_recording()
                        self.logger.info(f"ProcessWatcher: Recording started")
                        state = "RECORDING"
                
                elif state == "RECORDING":
                    # Check if process is still running
                    if not self.is_running(process_name):
                        self.logger.info(f"ProcessWatcher: Process {process_name} no longer running")
                        
                        # Stop recording
                        filepath = self.obs.stop_recording()
                        self.logger.info(f"ProcessWatcher: Recording stopped: {filepath}")
                        state = "DONE"
                        return filepath
                
                # Wait before next poll
                time.sleep(poll_interval)
            
            # Stopped manually
            self.logger.info("ProcessWatcher: Stopped manually")
            return ""
            
        except KeyboardInterrupt:
            self.logger.info("ProcessWatcher: Interrupted by user")
            return ""
    
    def stop(self) -> None:
        """Stop the watch loop cleanly."""
        self._stop_flag.set()