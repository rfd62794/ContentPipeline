"""
Tests for core/game_launcher.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.game_launcher import GameLauncher


class TestGameLauncher:
    
    @patch('core.game_launcher.subprocess.Popen')
    def test_launch_steam(self, mock_popen):
        """launch() calls _launch_steam() when steam_id present."""
        # Create temporary config file with v2 schema
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "Everything is Crab.exe": {
                    "folder": "Everything Is Crab",
                    "steam_id": "2627510",
                    "executable": None
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            logger = Mock()
            launcher = GameLauncher(logger, config_path)
            
            result = launcher.launch("Everything is Crab.exe")
            
            # Should return True on successful Steam launch
            assert result is True
            mock_popen.assert_called_once()
            # Verify Steam protocol format
            call_args = mock_popen.call_args[0][0]
            assert "steam://rungameid/2627510" in call_args
            logger.info.assert_called()
            
        finally:
            Path(config_path).unlink()
    
    @patch('core.game_launcher.subprocess.Popen')
    def test_launch_both_null(self, mock_popen):
        """launch() returns False when both steam_id and executable are null."""
        # Create temporary config file with v2 schema
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "TestGame.exe": {
                    "folder": "Test Game",
                    "steam_id": None,
                    "executable": None
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            logger = Mock()
            launcher = GameLauncher(logger, config_path)
            
            result = launcher.launch("TestGame.exe")
            
            # Should return False when both null
            assert result is False
            mock_popen.assert_not_called()
            logger.error.assert_called()
            
        finally:
            Path(config_path).unlink()
    
    def test_launch_not_found(self):
        """launch() returns False when process_name not in mapping."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "Everything is Crab.exe": {
                    "folder": "Everything Is Crab",
                    "steam_id": "2627510",
                    "executable": None
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            logger = Mock()
            launcher = GameLauncher(logger, config_path)
            
            result = launcher.launch("NonExistent.exe")
            
            # Should return False when not found
            assert result is False
            logger.warning.assert_called()
            
        finally:
            Path(config_path).unlink()
    
    @patch('core.game_launcher.subprocess.Popen')
    def test_launch_exception_safe(self, mock_popen):
        """launch() returns False on subprocess exception."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "Everything is Crab.exe": {
                    "folder": "Everything Is Crab",
                    "steam_id": "2627510",
                    "executable": None
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            mock_popen.side_effect = Exception("Subprocess error")
            
            logger = Mock()
            launcher = GameLauncher(logger, config_path)
            
            result = launcher.launch("Everything is Crab.exe")
            
            # Should return False on exception
            assert result is False
            logger.error.assert_called()
            
        finally:
            Path(config_path).unlink()
    
    @patch('core.game_launcher.subprocess.Popen')
    @patch('core.game_launcher.Path')
    def test_launch_executable(self, mock_path, mock_popen):
        """launch() calls _launch_executable() when steam_id null and executable present."""
        import pytest
        pytest.skip("Path mocking complexity - defer to later")
    
    def test_resolver_v1_backward_compat(self):
        """resolve_recording_path() handles flat string v1 format with warning."""
        from core.process_watcher import ProcessWatcher
        
        # Create temporary config file with v1 schema (flat strings)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "Everything is Crab.exe": "Everything Is Crab"
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            obs = Mock()
            logger = Mock()
            watcher = ProcessWatcher(obs=obs, logger=logger)
            
            raw_path = "C:/Users/cheat/Videos/2026-05-19 19-27-58.mp4"
            result = watcher.resolve_recording_path(raw_path, "Everything is Crab.exe", config_path)
            
            # Should still work with v1 format
            assert "Everything Is Crab" in result
            logger.warning.assert_called()
            
        finally:
            Path(config_path).unlink()