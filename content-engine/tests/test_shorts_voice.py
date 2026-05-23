"""
Tests for Shorts voice overlay feature.

Pure function tests only — no edge_tts or ffmpeg calls.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from produce_short import (
    should_generate_voice,
    build_voice_mix_filter,
    build_config_from_yaml,
    convert_beats_to_segments,
    compute_voice_schedule,
)


# =============================================================================
# should_generate_voice
# =============================================================================

class TestShouldGenerateVoice:
    """Test should_generate_voice pure function."""

    def test_normal_text_returns_true(self):
        assert should_generate_voice("The ground shook.") is True

    def test_single_word_returns_true(self):
        assert should_generate_voice("VICTORY!") is True

    def test_none_returns_false(self):
        assert should_generate_voice(None) is False

    def test_empty_string_returns_false(self):
        assert should_generate_voice("") is False

    def test_whitespace_only_returns_false(self):
        assert should_generate_voice("   ") is False

    def test_whitespace_only_tabs_returns_false(self):
        assert should_generate_voice("\t\n  ") is False

    def test_text_with_leading_whitespace_returns_true(self):
        assert should_generate_voice("  I was not ready.") is True

    def test_text_with_trailing_whitespace_returns_true(self):
        assert should_generate_voice("I got wings.  ") is True


# =============================================================================
# build_voice_mix_filter
# =============================================================================

class TestBuildVoiceMixFilter:
    """Test build_voice_mix_filter pure function."""

    def test_standard_volume(self):
        result = build_voice_mix_filter(0.50)
        assert "volume=0.5[v]" in result
        assert "amix=inputs=2" in result
        assert "[audio]" in result

    def test_low_volume(self):
        result = build_voice_mix_filter(0.25)
        assert "volume=0.25" in result

    def test_full_volume(self):
        result = build_voice_mix_filter(1.0)
        assert "volume=1.0" in result

    def test_filter_references_input_1_for_music(self):
        result = build_voice_mix_filter(0.5)
        assert "[1:a]" in result

    def test_filter_references_input_2_for_voice(self):
        result = build_voice_mix_filter(0.5)
        assert "[2:a]" in result

    def test_filter_uses_amix(self):
        result = build_voice_mix_filter(0.5)
        assert "amix" in result

    def test_returns_string(self):
        assert isinstance(build_voice_mix_filter(0.5), str)

    def test_default_delay(self):
        result = build_voice_mix_filter(0.5)
        assert "adelay=300|300" in result

    def test_custom_delay(self):
        result = build_voice_mix_filter(0.5, 0.5)
        assert "adelay=500|500" in result

    def test_zero_delay(self):
        result = build_voice_mix_filter(0.5, 0.0)
        assert "adelay=0|0" in result

    def test_delay_before_volume(self):
        result = build_voice_mix_filter(0.5, 0.3)
        # adelay should come before volume in the filter chain
        assert result.index("adelay") < result.index("volume")


# =============================================================================
# build_config_from_yaml — voice fields
# =============================================================================

class TestBuildConfigFromYamlVoice:
    """Test voice-related fields in build_config_from_yaml."""

    def test_voice_disabled_by_default(self):
        config = build_config_from_yaml({})
        assert config["voice_enabled"] is False

    def test_voice_enabled_from_yaml(self):
        config = build_config_from_yaml({"voice": True})
        assert config["voice_enabled"] is True

    def test_voice_volume_default(self):
        config = build_config_from_yaml({})
        assert config["voice_volume"] == 0.50

    def test_voice_volume_from_yaml(self):
        config = build_config_from_yaml({"voice_volume": 0.30})
        assert config["voice_volume"] == 0.30

    def test_voice_name_default(self):
        config = build_config_from_yaml({})
        assert config["voice_name"] == "David"

    def test_voice_name_from_yaml(self):
        config = build_config_from_yaml({"voice_name": "Zira"})
        assert config["voice_name"] == "Zira"

    def test_voice_false_explicit(self):
        config = build_config_from_yaml({"voice": False})
        assert config["voice_enabled"] is False

    def test_music_volume_unaffected(self):
        config = build_config_from_yaml({"voice": True, "music_volume": 0.15})
        assert config["music_volume"] == 0.15
        assert config["voice_enabled"] is True

    def test_voice_delay_default(self):
        config = build_config_from_yaml({})
        assert config["voice_delay"] == 0.3

    def test_voice_delay_from_yaml(self):
        config = build_config_from_yaml({"voice_delay": 0.5})
        assert config["voice_delay"] == 0.5

    def test_voice_delay_zero(self):
        config = build_config_from_yaml({"voice_delay": 0.0})
        assert config["voice_delay"] == 0.0

    def test_voice_gap_default(self):
        config = build_config_from_yaml({})
        assert config["voice_gap"] == 1.5

    def test_voice_gap_from_yaml(self):
        config = build_config_from_yaml({"voice_gap": 2.0})
        assert config["voice_gap"] == 2.0

    def test_voice_gap_zero(self):
        config = build_config_from_yaml({"voice_gap": 0.0})
        assert config["voice_gap"] == 0.0


# =============================================================================
# generate_voice_clip (Windows SAPI COM — requires win32com, not tested here)
# =============================================================================

# Tests skipped: generate_voice_clip now uses Windows SAPI COM (pywin32) which is
# not easily mockable and requires Windows COM infrastructure. The function is
# integration-tested by running produce_short.py end-to-end.


# =============================================================================
# compute_voice_schedule
# =============================================================================

class TestComputeVoiceSchedule:
    """Test compute_voice_schedule pure function."""

    def test_normal_gaps_no_collision(self):
        segments = [
            {"duration": 4.0},
            {"duration": 11.0},
            {"duration": 2.0},  # Increased to accommodate TTS
        ]
        tts_durations = [2.0, 2.0, 1.0]
        schedule = compute_voice_schedule(segments, tts_durations, voice_delay=0.3, voice_gap=1.5)
        
        # Segment 0: starts at 0.3, ends at 2.3
        assert schedule[0] == 0.3
        # Segment 1: starts at 4.3 (segment start + delay), gap from previous: 4.3 - 2.3 = 2.0s > 1.5s
        assert schedule[1] == 4.3
        # Segment 2: starts at 15.3, gap from previous: 15.3 - 6.3 = 9.0s > 1.5s
        assert schedule[2] == 15.3

    def test_collision_resolved_by_gap_constraint(self):
        segments = [
            {"duration": 3.0},
            {"duration": 3.0},
            {"duration": 4.0},  # Increased to accommodate delayed voice
        ]
        tts_durations = [2.0, 2.0, 2.0]
        schedule = compute_voice_schedule(segments, tts_durations, voice_delay=0.3, voice_gap=1.5)
        
        # Segment 0: starts at 0.3, ends at 2.3
        assert schedule[0] == 0.3
        # Segment 1: segment start at 3.0, but previous voice ends at 2.3
        # Gap constraint: 2.3 + 1.5 = 3.8
        # Segment start + delay: 3.0 + 0.3 = 3.3
        # Max: 3.8
        assert schedule[1] == 3.8
        # Segment 2: segment start at 6.0, previous voice ends at 3.8 + 2.0 = 5.8
        # Gap constraint: 5.8 + 1.5 = 7.3
        # Segment start + delay: 6.0 + 0.3 = 6.3
        # Max: 7.3
        assert schedule[2] == 7.3

    def test_segment_skipped_when_pushed_past_end(self):
        segments = [
            {"duration": 1.0},
            {"duration": 1.0},
        ]
        tts_durations = [2.0, 2.0]  # TTS longer than segment duration for both
        schedule = compute_voice_schedule(segments, tts_durations, voice_delay=0.3, voice_gap=1.5)
        
        # Segment 0: starts at 0.3, but would end at 2.3 > segment end (1.0)
        assert schedule[0] is None
        # Segment 1: starts at 1.3, but would end at 3.3 > segment end (2.0)
        assert schedule[1] is None

    def test_voice_gap_zero_no_constraint(self):
        segments = [
            {"duration": 3.0},
            {"duration": 3.0},
        ]
        tts_durations = [2.0, 2.0]
        schedule = compute_voice_schedule(segments, tts_durations, voice_delay=0.3, voice_gap=0.0)
        
        # With gap=0, voices can start immediately after previous ends
        # Segment 0: starts at 0.3, ends at 2.3
        assert schedule[0] == 0.3
        # Segment 1: segment start at 3.0, previous voice ends at 2.3
        # Gap constraint: 2.3 + 0.0 = 2.3
        # Segment start + delay: 3.0 + 0.3 = 3.3
        # Max: 3.3
        assert schedule[1] == 3.3

    def test_mixed_voice_and_silence(self):
        segments = [
            {"duration": 4.0},
            {"duration": 4.0},
            {"duration": 4.0},
        ]
        tts_durations = [2.0, 0.0, 2.0]  # Middle segment has no voice
        schedule = compute_voice_schedule(segments, tts_durations, voice_delay=0.3, voice_gap=1.5)
        
        # Segment 0: starts at 0.3
        assert schedule[0] == 0.3
        # Segment 1: no voice (duration 0.0)
        assert schedule[1] is None
        # Segment 2: segment start at 8.0, previous voice ended at 2.3
        # Gap constraint: 2.3 + 1.5 = 3.8
        # Segment start + delay: 8.0 + 0.3 = 8.3
        # Max: 8.3
        assert schedule[2] == 8.3

    def test_returns_correct_length(self):
        segments = [
            {"duration": 4.0},
            {"duration": 4.0},
        ]
        tts_durations = [2.0, 2.0]
        schedule = compute_voice_schedule(segments, tts_durations)
        assert len(schedule) == len(segments)

    def test_default_parameters(self):
        segments = [{"duration": 4.0}]
        tts_durations = [2.0]
        schedule = compute_voice_schedule(segments, tts_durations)
        # Should use default voice_delay=0.3, voice_gap=1.5
        assert schedule[0] == 0.3


# =============================================================================
# Voice path assignment in convert_beats_to_segments
# =============================================================================

class TestSegmentVoicePath:
    """Test that segments get voice_path=None by default from convert_beats_to_segments."""

    def test_convert_beats_no_voice_path(self):
        beats = [
            {"clip_start": "0:01", "clip_end": "0:05", "duration": 4, "line": "Test line."}
        ]
        segments = convert_beats_to_segments(beats, "source.mp4")
        # voice_path is not set by convert_beats_to_segments — it's added later in produce_short_from_yaml
        assert "voice_path" not in segments[0]

    def test_empty_line_beat(self):
        beats = [
            {"clip_start": "0:01", "clip_end": "0:05", "duration": 4, "line": ""}
        ]
        segments = convert_beats_to_segments(beats, "source.mp4")
        assert segments[0]["segment_text"] == ""

    def test_none_line_beat(self):
        beats = [
            {"clip_start": "0:01", "clip_end": "0:05", "duration": 4, "line": None}
        ]
        segments = convert_beats_to_segments(beats, "source.mp4")
        assert segments[0]["segment_text"] is None
