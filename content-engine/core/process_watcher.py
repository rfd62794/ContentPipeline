"""
Process Watcher — Detect game process and trigger OBS recording

Contract:
- is_running(process_name) returns True if process is running
- watch(process_name, scene, poll_interval) blocks until process exits after being detected
- All OBS calls go through obs parameter (duck typing — accepts any object with recording methods)
- Process name is never hardcoded — caller provides it
- Uses subprocess only (tasklist) — no external dependencies
"""

import subprocess
import time
import threading
from typing import Optional
from core.obs_manager import OBSManager


class ProcessWatcher:
    """Watch for a game process and trigger OBS recording automatically."""
    
    def __init__(self, obs, logger) -> None:
        """
        Initialize ProcessWatcher.
        
        Args:
            obs: Object with recording control methods (OBSManager or duck-typed mock)
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
            return process_name in result.stdout
        except Exception:
            return False
    
    def watch(self, process_name: str, scene: Optional[str] = None, poll_interval: int = 5, focus_watcher=None) -> str:
        """
        Watch for process and trigger OBS recording.
        
        This is a blocking call. It does not return until the game process
        has been detected AND subsequently closed.
        
        State machine: WAITING → RECORDING → DONE
        
        Args:
            process_name: Name of the process to watch for
            scene: Optional OBS scene to switch to before recording
            poll_interval: Seconds between process checks (default: 5)
            focus_watcher: Optional FocusWatcher for pause/resume on focus loss
            
        Returns:
            File path of recorded video, or empty string if stopped manually
        """
        self._stop_flag.clear()
        state = "WAITING"
        paused = False
        
        self.logger.info(f"ProcessWatcher: Waiting for {process_name}...")
        
        try:
            while not self._stop_flag.is_set():
                if state == "WAITING":
                    if self.is_running(process_name):
                        self.logger.info(f"ProcessWatcher: Detected {process_name}")
                        
                        if scene:
                            if self.obs.switch_scene(scene):
                                self.logger.info(f"ProcessWatcher: Switched to scene: {scene}")
                        
                        if self.obs.start_recording():
                            self.logger.info(f"ProcessWatcher: Recording started")
                            state = "RECORDING"
                
                elif state == "RECORDING":
                    if not self.is_running(process_name):
                        self.logger.info(f"ProcessWatcher: Process {process_name} no longer running")
                        
                        if paused:
                            if self.obs.resume_record():
                                self.logger.info(f"ProcessWatcher: Recording resumed before stop")
                        
                        filepath = self.obs.stop_recording()
                        if filepath:
                            self.logger.info(f"ProcessWatcher: Recording stopped: {filepath}")
                        
                        filepath = self.resolve_recording_path(filepath, process_name)
                        
                        state = "DONE"
                        return filepath
                    
                    if focus_watcher:
                        focused = focus_watcher.is_process_focused(process_name)
                        
                        if focused and paused:
                            if self.obs.resume_record():
                                self.logger.info(f"ProcessWatcher: Recording resumed — game regained focus")
                            paused = False
                        
                        elif not focused and not paused:
                            if self.obs.pause_record():
                                self.logger.info(f"ProcessWatcher: Recording paused — game lost focus")
                            paused = True
                
                time.sleep(poll_interval)
            
            self.logger.info("ProcessWatcher: Stopped manually")
            return ""
            
        except KeyboardInterrupt:
            self.logger.info("ProcessWatcher: Interrupted by user")
            return ""
    
    def stop(self) -> None:
        """Stop the watch loop cleanly."""
        self._stop_flag.set()
    
    def _get_folder(self, entry) -> str:
        """
        Extract folder name from mapping entry, handling both v1 and v2 schema.
        
        Args:
            entry: Mapping entry (string for v1, dict for v2)
            
        Returns:
            Folder name as string, or empty string if resolution fails
        """
        if isinstance(entry, str):
            self.logger.warning("ProcessWatcher: v1 schema detected (flat string), consider migrating to v2 dict format")
            return entry
        elif isinstance(entry, dict):
            return entry.get('folder', '')
        else:
            self.logger.warning(f"ProcessWatcher: Unknown schema format for entry: {type(entry)}")
            return ""
    
    def resolve_recording_path(self, raw_path: str, process_name: str, mapping_path: str = 'config/game_folders.json') -> str:
        """
        Resolve recording path to correct subfolder based on game mapping.
        
        Args:
            raw_path: Original file path from OBS
            process_name: Game process name (e.g., "Everything is Crab.exe")
            mapping_path: Path to game_folders.json config file
            
        Returns:
            Corrected path with subfolder inserted, or raw_path if resolution fails
        """
        import json
        import os
        from pathlib import Path
        
        try:
            mapping_file = Path(mapping_path)
            if not mapping_file.exists():
                self.logger.info(f"ProcessWatcher: No folder mapping found at {mapping_path}")
                return raw_path
            
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            
            entry = mapping.get(process_name)
            if not entry:
                self.logger.info(f"ProcessWatcher: No folder mapping for {process_name}")
                return raw_path
            
            subfolder = self._get_folder(entry)
            if not subfolder:
                self.logger.info(f"ProcessWatcher: No folder name found for {process_name}")
                return raw_path
            
            raw_path_obj = Path(raw_path)
            filename = raw_path_obj.name
            base_dir = raw_path_obj.parent.parent
            corrected_path = base_dir / subfolder / filename
            
            self.logger.info(f"ProcessWatcher: Resolved path: {raw_path} -> {corrected_path}")
            
            if raw_path_obj.exists():
                corrected_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.move(str(raw_path_obj), str(corrected_path))
                self.logger.info(f"ProcessWatcher: Moved file to {corrected_path}")
            
            return str(corrected_path)
            
        except json.JSONDecodeError as e:
            self.logger.info(f"ProcessWatcher: Malformed JSON in {mapping_path}: {e}")
            return raw_path
        except Exception as e:
            self.logger.info(f"ProcessWatcher: Path resolution failed: {e}")
            return raw_path
