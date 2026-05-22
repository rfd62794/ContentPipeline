"""
Unit tests for review_session.py pure functions.

These tests cover only the pure functions that have no external dependencies.
Integration functions (record_audio, launch_vlc, transcribe, main) are not tested here.
"""

import datetime
import sys
from pathlib import Path

import pytest

# Add repo root to path for import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import only pure functions to avoid dependency issues
from review_session import (
    format_timestamp,
    sanitize_slug,
    build_session_path,
    offset_segments,
    build_header,
    build_transcript,
)


class TestFormatTimestamp:
    """Test format_timestamp function."""
    
    def test_format_timestamp_minutes_only(self):
        """242.0 → "04:02" """
        assert format_timestamp(242.0) == "04:02"
    
    def test_format_timestamp_with_hours(self):
        """3661.5 → "01:01:01" """
        assert format_timestamp(3661.5) == "01:01:01"
    
    def test_format_timestamp_zero(self):
        """0.0 → "00:00" """
        assert format_timestamp(0.0) == "00:00"
    
    def test_format_timestamp_sub_minute(self):
        """45.0 → "00:45" """
        assert format_timestamp(45.0) == "00:45"


class TestSanitizeSlug:
    """Test sanitize_slug function."""
    
    def test_sanitize_slug_spaces(self):
        """Path with spaces in filename → underscores in slug."""
        result = sanitize_slug("C:/Videos/my video file.mp4")
        assert result == "my_video_file"
    
    def test_sanitize_slug_extension_stripped(self):
        """.mp4 extension not in output."""
        result = sanitize_slug("C:/Videos/test.mp4")
        assert result == "test"
        assert ".mp4" not in result
    
    def test_sanitize_slug_full_path(self):
        """Full Windows path → only filename stem."""
        result = sanitize_slug("C:/Users/cheat/Videos/Everything Is Crab/2026-05-19 19-27-58.mp4")
        assert result == "2026-05-19_19-27-58"
        assert "C:" not in result
        assert "Users" not in result


class TestOffsetSegments:
    """Test offset_segments function."""
    
    def test_offset_segments_adds_offset(self):
        """All start values incremented by offset."""
        segments = [
            {"start": 0.0, "text": "first"},
            {"start": 5.0, "text": "second"},
            {"start": 10.0, "text": "third"},
        ]
        result = offset_segments(segments, 242)
        assert result[0]["start"] == 242.0
        assert result[1]["start"] == 247.0
        assert result[2]["start"] == 252.0
    
    def test_offset_segments_no_mutation(self):
        """Input list unchanged after call."""
        segments = [
            {"start": 0.0, "text": "first"},
            {"start": 5.0, "text": "second"},
        ]
        original_start = segments[0]["start"]
        offset_segments(segments, 100)
        assert segments[0]["start"] == original_start
    
    def test_offset_segments_empty_list(self):
        """Empty input → empty output."""
        result = offset_segments([], 100)
        assert result == []


class TestBuildTranscript:
    """Test build_transcript function."""
    
    def test_build_transcript_contains_timestamps(self):
        """Output contains [04:02] format timestamps."""
        header = "# Review Session"
        segments = [
            {"start": 242.0, "text": "test text"},
        ]
        result = build_transcript(header, segments)
        assert "[04:02]" in result
    
    def test_build_transcript_header_present(self):
        """Output starts with # Review Session."""
        header = "# Review Session"
        segments = []
        result = build_transcript(header, segments)
        assert result.startswith("# Review Session")


class TestBuildHeader:
    """Test build_header function."""
    
    def test_build_header_offset_present(self):
        """Header contains 04:02 (242s) when start_time=242."""
        session_dt = datetime.datetime(2026, 5, 21, 22, 15, 30)
        result = build_header("test.mp4", 242, "base", session_dt, 5, "03:12")
        assert "04:02 (242s)" in result
    
    def test_build_header_model_present(self):
        """Header contains model name passed in."""
        session_dt = datetime.datetime(2026, 5, 21, 22, 15, 30)
        result = build_header("test.mp4", 0, "small", session_dt, 5, "03:12")
        assert "small" in result
