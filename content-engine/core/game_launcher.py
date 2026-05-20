"""
Game Launcher — Launch games via Steam protocol or direct executable

This module provides game launching functionality using either Steam protocol
(steam://rungameid/{id}) or direct executable path. It is used by the pipeline
to automatically launch games before watching for them.

Dependencies:
- subprocess — Process spawning
- pathlib — Path validation for executables
"""

import subprocess
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GameLauncher:
    """Launch games via Steam protocol or direct executable."""
    
    def __init__(self, logger, mapping_path: str = 'config/game_folders.json') -> None:
        """
        Initialize GameLauncher.
        
        Args:
            logger: Logger instance for operation logging
            mapping_path: Path to game_folders.json config file
        """
        self.logger = logger
        self.mapping_path = mapping_path
    
    def launch(self, process_name: str) -> bool:
        """
        Launch a game using Steam protocol or direct executable.
        
        Args:
            process_name: Process name to launch (e.g., "Everything is Crab.exe")
            
        Returns:
            True if launch command fired successfully, False otherwise
            Never raises — all exceptions caught and logged
        """
        import json
        
        try:
            # Load game_folders.json
            mapping_file = Path(self.mapping_path)
            if not mapping_file.exists():
                self.logger.warning(f"GameLauncher: No folder mapping found at {self.mapping_path}")
                return False
            
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            
            # Find entry for process_name
            entry = mapping.get(process_name)
            if not entry:
                self.logger.warning(f"GameLauncher: No entry found for {process_name}")
                return False
            
            # Handle both v1 (flat string) and v2 (dict) formats
            if isinstance(entry, str):
                self.logger.warning(f"GameLauncher: v1 schema detected for {process_name}, no launch method available")
                return False
            
            # v2 dict format
            steam_id = entry.get('steam_id')
            executable = entry.get('executable')
            
            if steam_id:
                return self._launch_steam(steam_id)
            elif executable:
                return self._launch_executable(executable)
            else:
                self.logger.error(f"GameLauncher: No launch method for {process_name} (both steam_id and executable are null)")
                return False
            
        except Exception as e:
            self.logger.error(f"GameLauncher: Failed to launch {process_name}: {e}")
            return False
    
    def _launch_steam(self, steam_id: str) -> bool:
        """
        Launch game via Steam protocol.
        
        Args:
            steam_id: Steam App ID (e.g., "2627510")
            
        Returns:
            True if launch command fired successfully, False on exception
            Never raises — all exceptions caught and logged
        """
        try:
            subprocess.Popen([
                "cmd", "/c", "start",
                f"steam://rungameid/{steam_id}"
            ])
            self.logger.info(f"GameLauncher: Launched {steam_id} via Steam")
            return True
        except Exception as e:
            self.logger.error(f"GameLauncher: Failed to launch via Steam: {e}")
            return False
    
    def _launch_executable(self, executable: str) -> bool:
        """
        Launch game via direct executable path.
        
        Args:
            executable: Path to executable file
            
        Returns:
            True if launch command fired successfully, False if path missing or exception
            Never raises — all exceptions caught and logged
        """
        try:
            # Verify executable path exists first
            exe_path = Path(executable)
            if not exe_path.exists():
                self.logger.error(f"GameLauncher: Executable not found: {executable}")
                return False
            
            subprocess.Popen([executable])
            self.logger.info(f"GameLauncher: Launched {executable}")
            return True
        except Exception as e:
            self.logger.error(f"GameLauncher: Failed to launch executable: {e}")
            return False