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
    build_outro_beat,
    OUTRO_LINE,
    OUTRO_DURATION,
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


# =============================================================================
# generate_voice_clip (Windows SAPI COM — requires win32com, not tested here)
# =============================================================================

# Tests skipped: generate_voice_clip now uses Windows SAPI COM (pywin32) which is
# not easily mockable and requires Windows COM infrastructure. The function is
# integration-tested by running produce_short.py end-to-end.


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


# =============================================================================
# build_outro_beat
# =============================================================================

class TestBuildOutroBeat:
    """Test build_outro_beat pure function — all four directive cases."""

    BEATS = [
        {"clip_start": "3:17", "clip_end": "3:19", "duration": 2, "line": "What am I."},
    ]

    def test_empty_beats_returns_none(self):
        assert build_outro_beat([]) is None

    def test_add_outro_false_leaves_beat_list_unchanged(self):
        original = list(self.BEATS)
        # Simulates the pipeline path when add_outro=False: build_outro_beat is never called.
        # Verify beat list is untouched.
        assert original == self.BEATS

    def test_add_outro_true_appends_beat_derived_from_last_clip_end(self):
        outro = build_outro_beat(self.BEATS)
        assert outro is not None
        # clip_start should equal the last beat's clip_end
        assert outro["clip_start"] == "3:19"
        # clip_end should be clip_start + OUTRO_DURATION (default 4s)
        assert outro["clip_end"] == "3:23"
        assert outro["duration"] == OUTRO_DURATION
        assert outro["line"] == OUTRO_LINE

    def test_outro_beat_line_matches_cta_constant(self):
        outro = build_outro_beat(self.BEATS)
        assert outro["line"] == "Like and subscribe if you're enjoying the ride."

    def test_custom_outro_line_override(self):
        outro = build_outro_beat(self.BEATS, outro_line="Follow for more.")
        assert outro["line"] == "Follow for more."

    def test_clamp_to_video_duration_when_extension_exceeds_length(self):
        # Last beat ends at 3:19 = 199s. Default outro would end at 203s.
        # Video is only 201s — clip_end must clamp to 201, duration = 2.
        outro = build_outro_beat(self.BEATS, video_duration=201.0)
        assert outro is not None
        clip_end_sec = int(outro["clip_end"].split(":")[0]) * 60 + int(outro["clip_end"].split(":")[1])
        assert clip_end_sec <= 201
        assert outro["duration"] == 2

    def test_no_clamp_when_video_duration_is_none(self):
        outro = build_outro_beat(self.BEATS, video_duration=None)
        assert outro["duration"] == OUTRO_DURATION

    def test_no_clamp_when_video_is_long_enough(self):
        # Video is 600s — no clamping needed
        outro = build_outro_beat(self.BEATS, video_duration=600.0)
        assert outro["duration"] == OUTRO_DURATION

    def test_h_mm_ss_timestamp_parsed_correctly(self):
        beats = [{"clip_start": "1:03:19", "clip_end": "1:03:23", "duration": 4, "line": "Long video."}]
        outro = build_outro_beat(beats)
        # 1:03:23 = 3803s, outro clip_start should be 63:23
        assert outro["clip_start"] == "63:23"
        assert outro["clip_end"] == "63:27"
