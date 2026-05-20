"""
Focus Watcher — foreground window detection for Windows.

This module provides foreground window detection using win32gui and win32process.
It is used to pause/resume recording when the target game loses/regains focus.

Dependencies:
- pywin32 (win32gui, win32process) — Windows API access
- psutil — Process name resolution from PID
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    import win32gui
    import win32process
    import psutil
except ImportError:
    win32gui = None
    win32process = None
    psutil = None


class FocusWatcher:
    """Detect foreground window and process focus state."""
    
    def __init__(self, logger) -> None:
        """
        Initialize FocusWatcher.
        
        Args:
            logger: Logger instance for operation logging
        """
        self.logger = logger
        if win32gui is None or win32process is None or psutil is None:
            self.logger.warning("FocusWatcher: Required Windows dependencies not available")
    
    def get_foreground_process(self) -> str:
        """
        Get the name of the current foreground process.
        
        Returns:
            Process name (e.g., "Everything is Crab.exe") or empty string on failure
            Never raises — all exceptions caught and logged
        """
        if win32gui is None or win32process is None or psutil is None:
            return ""
        
        try:
            # Get foreground window handle
            foreground_hwnd = win32gui.GetForegroundWindow()
            if not foreground_hwnd:
                return ""
            
            # Get process ID from window handle
            thread_id, process_id = win32process.GetWindowThreadProcessId(foreground_hwnd)
            if not process_id:
                return ""
            
            # Resolve PID to process name via psutil
            try:
                process = psutil.Process(process_id)
                return process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return ""
            
        except Exception as e:
            self.logger.error(f"FocusWatcher: Failed to get foreground process: {e}")
            return ""
    
    def is_process_focused(self, process_name: str) -> bool:
        """
        Check if the specified process is currently in foreground.
        
        Args:
            process_name: Process name to check (e.g., "Everything is Crab.exe")
            
        Returns:
            True if process is focused, False otherwise
            Comparison is case-insensitive
        """
        if not process_name:
            return False
        
        foreground_process = self.get_foreground_process()
        if not foreground_process:
            return False
        
        # Case-insensitive comparison
        return foreground_process.lower() == process_name.lower()