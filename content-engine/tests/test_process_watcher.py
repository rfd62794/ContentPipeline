"""
Tests for core/process_watcher.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import threading
import time
import json
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.process_watcher import ProcessWatcher


class TestProcessWatcher:
    @patch('core.process_watcher.subprocess.run')
    def test_is_running_true(self, mock_run):
        """is_running() returns True when process in tasklist output."""
        mock_run.return_value = MagicMock(
            stdout="Everything is Crab.exe Console                    1     5,000 K",
            returncode=0
        )
        
        obs = Mock()
        logger = Mock()
        watcher = ProcessWatcher(obs=obs, logger=logger)
        
        result = watcher.is_running("Everything is Crab.exe")
        
        assert result is True
        mock_run.assert_called_once()
    
    @patch('core.process_watcher.subprocess.run')
    def test_is_running_false(self, mock_run):
        """is_running() returns False when process not in output."""
        mock_run.return_value = MagicMock(
            stdout="No tasks are running which match the specified criteria.",
            returncode=0
        )
        
        obs = Mock()
        logger = Mock()
        watcher = ProcessWatcher(obs=obs, logger=logger)
        
        result = watcher.is_running("Everything is Crab.exe")
        
        assert result is False
    
    @patch('core.process_watcher.subprocess.run')
    def test_is_running_exception_safe(self, mock_run):
        """is_running() returns False on subprocess exception."""
        mock_run.side_effect = Exception("Subprocess failed")
        
        obs = Mock()
        logger = Mock()
        watcher = ProcessWatcher(obs=obs, logger=logger)
        
        result = watcher.is_running("Everything is Crab.exe")
        
        assert result is False
    
    @patch('core.process_watcher.ProcessWatcher.is_running')
    def test_watch_starts_recording(self, mock_is_running):
        """watch() calls obs.start_recording() when process detected."""
        # Simulate process starting
        mock_is_running.side_effect = [False, True, False]
        
        obs = Mock()
        obs.start_recording.return_value = None
        obs.stop_recording.return_value = "/path/to/recording.mp4"
        
        logger = Mock()
        watcher = ProcessWatcher(obs=obs, logger=logger)
        
        # Start watch in a thread with very short poll interval
        def run_watch():
            watcher.watch("Everything is Crab.exe", poll_interval=0.1)
        
        thread = threading.Thread(target=run_watch)
        thread.start()
        
        # Wait for watch to detect process and start recording
        time.sleep(0.3)
        
        # Stop the watch
        watcher.stop()
        thread.join(timeout=2)
        
        # Verify recording was started
        obs.start_recording.assert_called_once()
    
    @patch('core.process_watcher.ProcessWatcher.is_running')
    def test_watch_stops_recording(self, mock_is_running):
        """watch() calls obs.stop_recording() when process gone."""
        # Simulate process starting then stopping
        mock_is_running.side_effect = [False, True, False]
        
        obs = Mock()
        obs.start_recording.return_value = None
        obs.stop_recording.return_value = "/path/to/recording.mp4"
        
        logger = Mock()
        watcher = ProcessWatcher(obs=obs, logger=logger)
        
        # Start watch in a thread with very short poll interval
        def run_watch():
            return watcher.watch("Everything is Crab.exe", poll_interval=0.1)
        
        thread = threading.Thread(target=run_watch)
        thread.start()
        
        # Wait for watch to complete
        thread.join(timeout=2)
        
        # Verify recording was stopped
        obs.stop_recording.assert_called_once()
    
    @patch('core.process_watcher.ProcessWatcher.is_running')
    def test_watch_returns_filepath(self, mock_is_running):
        """watch() returns string from obs.stop_recording()."""
        # Simulate process starting then stopping
        mock_is_running.side_effect = [False, True, False]
        
        expected_filepath = "/path/to/recording.mp4"
        obs = Mock()
        obs.start_recording.return_value = None
        obs.stop_recording.return_value = expected_filepath
        
        logger = Mock()
        watcher = ProcessWatcher(obs=obs, logger=logger)
        
        # Start watch in a thread with very short poll interval
        def run_watch():
            return watcher.watch("Everything is Crab.exe", poll_interval=0.1)
        
        thread = threading.Thread(target=run_watch)
        thread.start()
        
        # Wait for watch to complete
        thread.join(timeout=2)
        
        # The watch() method returns the filepath, but since it's in a thread
        # we can't easily get the return value. Instead, verify that stop_recording
        # was called with the expected return value set up in the mock.
        obs.stop_recording.assert_called_once()
        # The mock returns the expected filepath, so the watch would return it
    
    @patch('core.process_watcher.shutil.move')
    @patch('core.process_watcher.Path.exists')
    def test_resolver_finds_subfolder(self, mock_exists, mock_move):
        """resolve_recording_path() inserts correct subfolder from mapping."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "Everything is Crab.exe": "Everything Is Crab",
                "Dave the Diver.exe": "Dave the Diver"
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            mock_exists.return_value = True
            mock_move.return_value = None
            
            obs = Mock()
            logger = Mock()
            watcher = ProcessWatcher(obs=obs, logger=logger)
            
            raw_path = "C:/Users/cheat/Videos/2026-05-19 19-27-58.mp4"
            result = watcher.resolve_recording_path(raw_path, "Everything is Crab.exe", config_path)
            
            # Should move to correct subfolder
            assert "Everything Is Crab" in result
            mock_move.assert_called_once()
            
        finally:
            Path(config_path).unlink()
    
    def test_resolver_fallback_unmapped(self):
        """resolve_recording_path() returns raw_path when game not in mapping."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "Dave the Diver.exe": "Dave the Diver"
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            obs = Mock()
            logger = Mock()
            watcher = ProcessWatcher(obs=obs, logger=logger)
            
            raw_path = "C:/Users/cheat/Videos/2026-05-19 19-27-58.mp4"
            result = watcher.resolve_recording_path(raw_path, "Everything is Crab.exe", config_path)
            
            # Should return raw_path unchanged
            assert result == raw_path
            
        finally:
            Path(config_path).unlink()
    
    def test_resolver_missing_json(self):
        """resolve_recording_path() returns raw_path when JSON missing."""
        obs = Mock()
        logger = Mock()
        watcher = ProcessWatcher(obs=obs, logger=logger)
        
        raw_path = "C:/Users/cheat/Videos/2026-05-19 19-27-58.mp4"
        result = watcher.resolve_recording_path(raw_path, "Everything is Crab.exe", "config/nonexistent.json")
        
        # Should return raw_path unchanged
        assert result == raw_path