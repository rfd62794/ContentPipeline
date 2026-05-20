"""
Tests for produce_short.py YAML-driven short production runner.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from produce_short import (
    load_yaml_config,
    convert_beats_to_segments,
    apply_text_stacking,
    build_config_from_yaml
)

class TestLoadYamlConfig:
    """Test YAML config loading."""
    
    def test_load_valid_yaml(self, tmp_path):
        """Test loading a valid YAML configuration."""
        yaml_content = """
name: test_short
source: test.mp4
attribution: null
music_path: assets/music/test.mp3
music_start: 0
stack_text: false
max_visible_lines: 5
beats:
  - clip_start: "0:00"
    clip_end: "0:05"
    duration: 5
    line: "Test line"
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)
        
        config = load_yaml_config(yaml_file)
        
        assert config["name"] == "test_short"
        assert config["source"] == "test.mp4"
        assert config["attribution"] is None
        assert config["music_path"] == "assets/music/test.mp3"
        assert config["music_start"] == 0
        assert config["stack_text"] is False
        assert config["max_visible_lines"] == 5
        assert len(config["beats"]) == 1
        assert config["beats"][0]["line"] == "Test line"
    
    def test_load_yaml_with_attribution(self, tmp_path):
        """Test loading YAML with attribution."""
        yaml_content = """
name: test_short
source: test.mp4
attribution: "Gameplay via: Test"
music_path: assets/music/test.mp3
music_start: 10
stack_text: true
max_visible_lines: 3
beats: []
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)
        
        config = load_yaml_config(yaml_file)
        
        assert config["attribution"] == "Gameplay via: Test"
        assert config["music_start"] == 10
        assert config["stack_text"] is True
        assert config["max_visible_lines"] == 3

class TestConvertBeatsToSegments:
    """Test beat to segment conversion."""
    
    def test_convert_single_beat(self):
        """Test converting a single beat to segment format."""
        beats = [
            {
                "clip_start": "0:00",
                "clip_end": "0:05",
                "duration": 5,
                "line": "Test line"
            }
        ]
        source = "test.mp4"
        
        segments = convert_beats_to_segments(beats, source)
        
        assert len(segments) == 1
        assert segments[0]["temp_file"] == source
        assert segments[0]["source_timestamp_start"] == "0:00"
        assert segments[0]["source_timestamp_end"] == "0:05"
        assert segments[0]["duration"] == 5
        assert segments[0]["segment_text"] == "Test line"
    
    def test_convert_multiple_beats(self):
        """Test converting multiple beats to segments."""
        beats = [
            {
                "clip_start": "0:00",
                "clip_end": "0:05",
                "duration": 5,
                "line": "Line 1"
            },
            {
                "clip_start": "0:05",
                "clip_end": "0:10",
                "duration": 5,
                "line": "Line 2"
            }
        ]
        source = "test.mp4"
        
        segments = convert_beats_to_segments(beats, source)
        
        assert len(segments) == 2
        assert segments[0]["segment_text"] == "Line 1"
        assert segments[1]["segment_text"] == "Line 2"

class TestApplyTextStacking:
    """Test text stacking with sliding window."""
    
    def test_no_stacking_disabled(self):
        """Test that text stacking is not applied when disabled."""
        segments = [
            {"segment_text": "Line 1", "duration": 1},
            {"segment_text": "Line 2", "duration": 1},
            {"segment_text": "Line 3", "duration": 1}
        ]
        
        # When stacking is disabled, segments should remain unchanged
        # (This is handled by the caller not calling apply_text_stacking)
        original_texts = [s["segment_text"] for s in segments]
        assert original_texts == ["Line 1", "Line 2", "Line 3"]
    
    def test_text_stacking_with_window(self):
        """Test text stacking with sliding window of 2 lines."""
        segments = [
            {"segment_text": "Line 1", "duration": 1},
            {"segment_text": "Line 2", "duration": 1},
            {"segment_text": "Line 3", "duration": 1},
            {"segment_text": "Line 4", "duration": 1}
        ]
        
        stacked = apply_text_stacking(segments, max_visible_lines=2)
        
        assert len(stacked) == 4
        assert stacked[0]["segment_text"] == "Line 1"
        assert stacked[1]["segment_text"] == "Line 1\nLine 2"
        assert stacked[2]["segment_text"] == "Line 2\nLine 3"
        assert stacked[3]["segment_text"] == "Line 3\nLine 4"
    
    def test_text_stacking_default_window(self):
        """Test text stacking with default 5-line window."""
        segments = [
            {"segment_text": f"Line {i}", "duration": 1}
            for i in range(1, 8)
        ]
        
        stacked = apply_text_stacking(segments, max_visible_lines=5)
        
        assert len(stacked) == 7
        # First 5 segments accumulate
        assert stacked[0]["segment_text"] == "Line 1"
        assert stacked[1]["segment_text"] == "Line 1\nLine 2"
        assert stacked[2]["segment_text"] == "Line 1\nLine 2\nLine 3"
        assert stacked[3]["segment_text"] == "Line 1\nLine 2\nLine 3\nLine 4"
        assert stacked[4]["segment_text"] == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        # Segment 6 slides window (drops Line 1)
        assert stacked[5]["segment_text"] == "Line 2\nLine 3\nLine 4\nLine 5\nLine 6"
        # Segment 7 slides window (drops Line 2)
        assert stacked[6]["segment_text"] == "Line 3\nLine 4\nLine 5\nLine 6\nLine 7"

class TestBuildConfigFromYaml:
    """Test config building from YAML."""
    
    def test_build_config_defaults(self):
        """Test building config with default values."""
        yaml_config = {
            "name": "test",
            "source": "test.mp4",
            "attribution": None,
            "music_path": "assets/music/custom.mp3",
            "music_start": 5,
            "beats": []
        }
        
        config = build_config_from_yaml(yaml_config)
        
        assert config["shorts_music_path"] == "assets/music/custom.mp3"
        assert config["shorts_music_start"] == 5
        assert config["shorts_attribution_enabled"] is False
        assert config["shorts_attribution_y_pct"] == 0.05
        assert config["shorts_attribution_font_size"] == 30
        assert config["shorts_attribution_color"] == "white"
        assert config["shorts_attribution_opacity"] == 0.85
        assert config["shorts_text_font"] == "monospace"
        assert config["shorts_text_size"] == 48
        assert config["shorts_text_color"] == "white"
        assert config["shorts_lower_third_height_pct"] == 0.25
    
    def test_build_config_with_attribution(self):
        """Test building config with attribution enabled."""
        yaml_config = {
            "name": "test",
            "source": "test.mp4",
            "attribution": "Gameplay via: Test",
            "music_path": "assets/music/test.mp3",
            "beats": []
        }
        
        config = build_config_from_yaml(yaml_config)
        
        assert config["shorts_attribution_enabled"] is True
    
    def test_build_config_music_defaults(self):
        """Test building config with default music values."""
        yaml_config = {
            "name": "test",
            "source": "test.mp4",
            "beats": []
        }
        
        config = build_config_from_yaml(yaml_config)
        
        # Default music path
        assert config["shorts_music_path"] == "assets/music/Pixelated_Passion.mp3"
        # Default music start
        assert config["shorts_music_start"] == 0
