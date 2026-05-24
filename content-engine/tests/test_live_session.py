"""
Tests for live_session.py pure functions.
Pure function tests only - no hardware, no audio recording.
"""

import datetime
from pathlib import Path
import sys

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from live_session import (
    build_session_header,
    build_live_transcript,
    get_process_name_for_game
)


class TestBuildSessionHeader:
    """Tests for build_session_header function."""
    
    def test_build_session_header_basic(self):
        """Returns formatted header with all fields."""
        game = "Dorfromantik"
        date = datetime.datetime(2026, 5, 23, 19, 45, 0)
        duration = "00:23:14"
        model = "base"
        
        result = build_session_header(game, date, duration, model)
        
        assert "# Live Session" in result
        assert "# Game: Dorfromantik" in result
        assert "# Date: 2026-05-23 19:45:00" in result
        assert "# Duration: 00:23:14" in result
        assert "# Model: base" in result
    
    def test_build_session_header_format(self):
        """Header follows exact format with # prefix on each line."""
        game = "TestGame"
        date = datetime.datetime(2026, 5, 23, 12, 0, 0)
        duration = "01:00:00"
        model = "small"
        
        result = build_session_header(game, date, duration, model)
        
        lines = result.split('\n')
        for line in lines:
            assert line.startswith("#"), f"Line doesn't start with #: {line}"


class TestBuildLiveTranscript:
    """Tests for build_live_transcript function."""
    
    def test_build_live_transcript_basic(self):
        """Assembles header and segments into transcript."""
        header = "# Live Session\n# Game: TestGame"
        segments = [
            {"start": 134.0, "text": "first segment"},
            {"start": 273.0, "text": "second segment"}
        ]
        
        result = build_live_transcript(header, segments)
        
        assert "# Live Session" in result
        assert "[02:14] first segment" in result
        assert "[04:33] second segment" in result
    
    def test_build_live_transcript_empty_segments(self):
        """Handles empty segments list gracefully."""
        header = "# Live Session\n# Game: TestGame"
        segments = []
        
        result = build_live_transcript(header, segments)
        
        assert "# Live Session" in result
        # Header has 2 lines + 1 blank line = 3 total lines
        assert result.count("\n") == 2  # 2 newlines for 3 lines


class TestGetProcessNameForGame:
    """Tests for get_process_name_for_game function."""
    
    def test_get_process_name_for_game_found(self):
        """Returns process name when game found in registry."""
        registry = {
            "123": {"exe_name": "Dorfromantik.exe", "window_title": "Dorfromantik"}
        }
        
        result = get_process_name_for_game("Dorfromantik", registry)
        
        assert result == "Dorfromantik.exe"
    
    def test_get_process_name_for_game_not_found(self):
        """Returns None when game not in registry."""
        registry = {
            "123": {"exe_name": "OtherGame.exe", "window_title": "OtherGame"}
        }
        
        result = get_process_name_for_game("NonExistent", registry)
        
        assert result is None
    
    def test_get_process_name_for_game_case_insensitive(self):
        """Case-insensitive matching on game name."""
        registry = {
            "123": {"exe_name": "Dorfromantik.exe", "window_title": "Dorfromantik"}
        }
        
        result = get_process_name_for_game("dorfromantik", registry)
        
        assert result == "Dorfromantik.exe"
    
    def test_get_process_name_for_game_window_title_match(self):
        """Matches against window_title field as well."""
        registry = {
            "123": {"exe_name": "game.exe", "window_title": "My Awesome Game"}
        }
        
        result = get_process_name_for_game("Awesome Game", registry)
        
        assert result == "game.exe"