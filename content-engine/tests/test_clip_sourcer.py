"""
Tests for core/clip_sourcer.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.clip_sourcer import ClipSourcer


class TestClipSourcer:
    @patch('core.clip_sourcer.subprocess.run')
    def test_clip_sourcer_download(self, mock_run):
        """download_clip() calls yt-dlp with correct args."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Mock()
            sourcer = ClipSourcer(tmpdir, logger)
            
            result = sourcer.download_clip(
                "https://www.youtube.com/watch?v=LUTPCMkA7xQ",
                "10:00",
                "10:30",
                "test_clip.mp4"
            )
            
            # Verify yt-dlp was called
            assert mock_run.called
            call_args = mock_run.call_args[0]
            assert call_args[0] == "yt-dlp"
    
    @patch('core.clip_sourcer.subprocess.run')
    def test_clip_sourcer_returns_path(self, mock_run):
        """download_clip() returns filepath string on success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the output file to simulate successful download
            output_file = Path(tmpdir) / "test_clip.mp4"
            output_file.write_text("mock")
            
            logger = Mock()
            sourcer = ClipSourcer(tmpdir, logger)
            
            result = sourcer.download_clip(
                "https://www.youtube.com/watch?v=LUTPCMkA7xQ",
                "10:00",
                "10:30"
            )
            
            # Should return the filepath
            assert result != ""
    
    @patch('core.clip_sourcer.subprocess.run')
    def test_clip_sourcer_failure_safe(self, mock_run):
        """download_clip() returns empty string on yt-dlp failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Download failed")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Mock()
            sourcer = ClipSourcer(tmpdir, logger)
            
            result = sourcer.download_clip(
                "https://www.youtube.com/watch?v=LUTPCMkA7xQ",
                "10:00",
                "10:30"
            )
            
            # Should return empty string on failure
            assert result == ""
    
    @patch('core.clip_sourcer.subprocess.run')
    def test_clip_sourcer_creates_dir(self, mock_run):
        """download_clip() creates output_dir if missing."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        
        # Use a non-existent directory
        import shutil
        non_existent_dir = tempfile.mktemp()
        shutil.rmtree(non_existent_dir)
        
        try:
            logger = Mock()
            sourcer = ClipSourcer(non_existent_dir, logger)
            
            result = sourcer.download_clip(
                "https://www.youtube.com/watch?v=LUTPCMkA7xQ",
                "10:00",
                "10:30"
            )
            
            # Directory should be created
            assert Path(non_existent_dir).exists()
            
        finally:
            shutil.rmtree(non_existent_dir, ignore_errors=True)
    
    def test_clip_sourcer_clip_exists(self):
        """clip_exists() returns True when file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Mock()
            sourcer = ClipSourcer(tmpdir, logger)
            
            # Create a test file
            test_file = Path(tmpdir) / "test.mp4"
            test_file.write_text("test")
            
            assert sourcer.clip_exists(str(test_file)) is True
            assert sourcer.clip_exists(str(Path(tmpdir) / "nonexistent.mp4")) is False