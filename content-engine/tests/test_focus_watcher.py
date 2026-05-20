"""
Tests for core/focus_watcher.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.focus_watcher import FocusWatcher


class TestFocusWatcher:
    
    @patch('core.focus_watcher.win32gui')
    @patch('core.focus_watcher.win32process')
    @patch('core.focus_watcher.psutil')
    def test_get_foreground_returns_name(self, mock_psutil, mock_win32process, mock_win32gui):
        """get_foreground_process() returns process name string."""
        # Mock win32gui
        mock_win32gui.GetForegroundWindow.return_value = 12345
        
        # Mock win32process
        mock_win32process.GetWindowThreadProcessId.return_value = (1234, 5678)
        
        # Mock psutil
        mock_process = Mock()
        mock_process.name.return_value = "Everything is Crab.exe"
        mock_psutil.Process.return_value = mock_process
        
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.get_foreground_process()
        assert result == "Everything is Crab.exe"
        mock_win32gui.GetForegroundWindow.assert_called_once()
        mock_win32process.GetWindowThreadProcessId.assert_called_once_with(12345)
        mock_psutil.Process.assert_called_once_with(5678)
    
    @patch('core.focus_watcher.win32gui')
    def test_get_foreground_exception_safe(self, mock_win32gui):
        """get_foreground_process() returns empty string on win32 exception."""
        mock_win32gui.GetForegroundWindow.side_effect = Exception("Win32 error")
        
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.get_foreground_process()
        assert result == ""
        logger.error.assert_called_once()
    
    @patch('core.focus_watcher.win32gui')
    @patch('core.focus_watcher.win32process')
    @patch('core.focus_watcher.psutil')
    def test_get_foreground_no_window(self, mock_psutil, mock_win32process, mock_win32gui):
        """get_foreground_process() returns empty string when no foreground window."""
        mock_win32gui.GetForegroundWindow.return_value = None
        
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.get_foreground_process()
        assert result == ""
    
    @patch('core.focus_watcher.win32gui')
    @patch('core.focus_watcher.win32process')
    @patch('core.focus_watcher.psutil')
    def test_get_foreground_no_pid(self, mock_psutil, mock_win32process, mock_win32gui):
        """get_foreground_process() returns empty string when no PID returned."""
        mock_win32gui.GetForegroundWindow.return_value = 12345
        mock_win32process.GetWindowThreadProcessId.return_value = (1234, None)
        
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.get_foreground_process()
        assert result == ""
    
    @patch('core.focus_watcher.win32gui')
    @patch('core.focus_watcher.win32process')
    @patch('core.focus_watcher.psutil')
    def test_get_foreground_psutil_exception(self, mock_psutil, mock_win32process, mock_win32gui):
        """get_foreground_process() returns empty string on psutil exception."""
        mock_win32gui.GetForegroundWindow.return_value = 12345
        mock_win32process.GetWindowThreadProcessId.return_value = (1234, 5678)
        mock_psutil.Process.side_effect = Exception("Process error")
        
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.get_foreground_process()
        assert result == ""
    
    @patch('core.focus_watcher.win32gui')
    @patch('core.focus_watcher.win32process')
    @patch('core.focus_watcher.psutil')
    def test_is_focused_true(self, mock_psutil, mock_win32process, mock_win32gui):
        """is_process_focused() returns True when foreground matches."""
        mock_win32gui.GetForegroundWindow.return_value = 12345
        mock_win32process.GetWindowThreadProcessId.return_value = (1234, 5678)
        
        mock_process = Mock()
        mock_process.name.return_value = "Everything is Crab.exe"
        mock_psutil.Process.return_value = mock_process
        
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.is_process_focused("Everything is Crab.exe")
        assert result is True
    
    @patch('core.focus_watcher.win32gui')
    @patch('core.focus_watcher.win32process')
    @patch('core.focus_watcher.psutil')
    def test_is_focused_false(self, mock_psutil, mock_win32process, mock_win32gui):
        """is_process_focused() returns False when foreground differs."""
        mock_win32gui.GetForegroundWindow.return_value = 12345
        mock_win32process.GetWindowThreadProcessId.return_value = (1234, 5678)
        
        mock_process = Mock()
        mock_process.name.return_value = "Chrome.exe"
        mock_psutil.Process.return_value = mock_process
        
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.is_process_focused("Everything is Crab.exe")
        assert result is False
    
    @patch('core.focus_watcher.win32gui')
    @patch('core.focus_watcher.win32process')
    @patch('core.focus_watcher.psutil')
    def test_is_focused_case_insensitive(self, mock_psutil, mock_win32process, mock_win32gui):
        """is_process_focused() matches regardless of case."""
        mock_win32gui.GetForegroundWindow.return_value = 12345
        mock_win32process.GetWindowThreadProcessId.return_value = (1234, 5678)
        
        mock_process = Mock()
        mock_process.name.return_value = "everything is crab.exe"
        mock_psutil.Process.return_value = mock_process
        
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.is_process_focused("Everything is Crab.exe")
        assert result is True
    
    @patch('core.focus_watcher.win32gui')
    @patch('core.focus_watcher.win32process')
    @patch('core.focus_watcher.psutil')
    def test_is_focused_empty_process_name(self, mock_psutil, mock_win32process, mock_win32gui):
        """is_process_focused() returns False when process_name is empty."""
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.is_process_focused("")
        assert result is False
    
    @patch('core.focus_watcher.win32gui')
    @patch('core.focus_watcher.win32process')
    @patch('core.focus_watcher.psutil')
    def test_is_focused_no_foreground(self, mock_psutil, mock_win32process, mock_win32gui):
        """is_process_focused() returns False when get_foreground_process returns empty."""
        mock_win32gui.GetForegroundWindow.return_value = None
        
        logger = Mock()
        watcher = FocusWatcher(logger)
        
        result = watcher.is_process_focused("Everything is Crab.exe")
        assert result is False