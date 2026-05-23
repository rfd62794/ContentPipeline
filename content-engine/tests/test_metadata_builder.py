"""
Tests for Metadata Builder

All tests use pure functions with mocked file I/O.
No network calls, no real OAuth, no real file I/O beyond fixture data.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock
import yaml
import tempfile
import os

from metadata_builder import (
    load_short_yaml,
    load_meta_yaml,
    resolve_metadata,
    generate_title_layer1,
    generate_description_layer1,
    generate_tags_layer1,
    validate_metadata,
    format_schedule
)


# =============================================================================
# Load YAML Tests
# =============================================================================

class TestLoadShortYaml:
    """Tests for load_short_yaml function."""
    
    def test_load_short_yaml_success(self, tmp_path):
        """Test successful loading of short YAML."""
        short_data = {
            'name': 'eic_short_1_evolution',
            'source': 'path/to/video.mp4',
            'beats': [
                {'clip_start': '0:00', 'clip_end': '0:10', 'duration': 10, 'line': 'Test'}
            ]
        }
        
        short_file = tmp_path / "test_short.yaml"
        with open(short_file, 'w') as f:
            yaml.dump(short_data, f)
        
        result = load_short_yaml(str(short_file))
        
        assert result == short_data
        assert result['name'] == 'eic_short_1_evolution'
    
    def test_load_short_yaml_not_found(self):
        """Test handling of missing file."""
        with pytest.raises(FileNotFoundError):
            load_short_yaml("nonexistent.yaml")
    
    def test_load_short_yaml_invalid_yaml(self, tmp_path):
        """Test handling of invalid YAML."""
        short_file = tmp_path / "invalid.yaml"
        with open(short_file, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")
        
        with pytest.raises(yaml.YAMLError):
            load_short_yaml(str(short_file))


class TestLoadMetaYaml:
    """Tests for load_meta_yaml function."""
    
    def test_load_meta_yaml_success(self, tmp_path):
        """Test successful loading of meta YAML."""
        meta_data = {
            'auto_generate': True,
            'title': 'Manual Title',
            'description': 'Manual Description',
            'tags': ['tag1', 'tag2'],
            'privacy': 'public',
            'schedule': '2026-05-23T21:00:00',
            'category_id': '20',
            'made_for_kids': False
        }
        
        meta_file = tmp_path / "test.meta.yaml"
        with open(meta_file, 'w') as f:
            yaml.dump(meta_data, f)
        
        result = load_meta_yaml(str(meta_file))
        
        assert result == meta_data
        assert result['auto_generate'] is True
    
    def test_load_meta_yaml_defaults_when_missing(self):
        """Test default values when file doesn't exist."""
        result = load_meta_yaml("nonexistent.meta.yaml")
        
        assert result['auto_generate'] is False
        assert result['title'] == ''
        assert result['description'] == ''
        assert result['tags'] == []
        assert result['privacy'] == 'public'
        assert result['schedule'] == ''
        assert result['category_id'] == '20'
        assert result['made_for_kids'] is False
    
    def test_load_meta_yaml_partial_override(self, tmp_path):
        """Test partial override with defaults for missing fields."""
        meta_data = {
            'title': 'Manual Title',
            'privacy': 'unlisted'
        }
        
        meta_file = tmp_path / "partial.meta.yaml"
        with open(meta_file, 'w') as f:
            yaml.dump(meta_data, f)
        
        result = load_meta_yaml(str(meta_file))
        
        assert result['title'] == 'Manual Title'
        assert result['privacy'] == 'unlisted'
        assert result['auto_generate'] is False  # Default
        assert result['description'] == ''  # Default
        assert result['tags'] == []  # Default


# =============================================================================
# Resolve Metadata Tests
# =============================================================================

class TestResolveMetadata:
    """Tests for resolve_metadata function."""
    
    def test_resolve_layer3_wins(self):
        """Test manual title overrides auto even when auto_generate true."""
        short = {'name': 'eic_short_1', 'beats': []}
        meta = {
            'auto_generate': True,
            'title': 'Manual Title',
            'description': '',
            'tags': [],
            'privacy': 'public',
            'schedule': '',
            'category_id': '20',
            'made_for_kids': False
        }
        steam = {'name': 'Game Name', 'description': 'Steam desc', 'genres': ['Action'], 'tags': []}
        
        result = resolve_metadata(short, meta, steam)
        
        assert result['title'] == 'Manual Title'  # Manual wins
    
    def test_resolve_layer1_used_when_empty(self):
        """Test empty title + auto_generate true -> Layer 1 result."""
        short = {'name': 'eic_short_1', 'beats': []}
        meta = {
            'auto_generate': True,
            'title': '',
            'description': '',
            'tags': [],
            'privacy': 'public',
            'schedule': '',
            'category_id': '20',
            'made_for_kids': False
        }
        steam = {'name': 'Game Name', 'description': 'Steam desc', 'genres': ['Action'], 'tags': []}
        
        result = resolve_metadata(short, meta, steam)
        
        assert result['title'] != ''  # Layer 1 generated
        assert 'Game Name' in result['title']
    
    def test_resolve_auto_generate_false(self):
        """Test empty title + auto_generate false -> empty string returned."""
        short = {'name': 'eic_short_1', 'beats': []}
        meta = {
            'auto_generate': False,
            'title': '',
            'description': '',
            'tags': [],
            'privacy': 'public',
            'schedule': '',
            'category_id': '20',
            'made_for_kids': False
        }
        steam = {'name': 'Game Name', 'description': 'Steam desc', 'genres': ['Action'], 'tags': []}
        
        result = resolve_metadata(short, meta, steam)
        
        assert result['title'] == ''  # No Layer 1 when auto_generate false
    
    def test_resolve_no_mutation(self):
        """Test input dicts unchanged after call."""
        short = {'name': 'eic_short_1', 'beats': []}
        meta = {
            'auto_generate': True,
            'title': '',
            'description': '',
            'tags': [],
            'privacy': 'public',
            'schedule': '',
            'category_id': '20',
            'made_for_kids': False
        }
        steam = {'name': 'Game Name', 'description': 'Steam desc', 'genres': ['Action'], 'tags': []}
        
        short_copy = short.copy()
        meta_copy = meta.copy()
        steam_copy = steam.copy()
        
        resolve_metadata(short, meta, steam)
        
        assert short == short_copy
        assert meta == meta_copy
        assert steam == steam_copy
    
    def test_resolve_partial_override(self):
        """Test title manual, tags empty + auto -> tags from Layer 1."""
        short = {'name': 'eic_short_1', 'beats': []}
        meta = {
            'auto_generate': True,
            'title': 'Manual Title',
            'description': '',
            'tags': [],
            'privacy': 'public',
            'schedule': '',
            'category_id': '20',
            'made_for_kids': False
        }
        steam = {'name': 'Game Name', 'description': 'Steam desc', 'genres': ['Action'], 'tags': ['tag1']}
        
        result = resolve_metadata(short, meta, steam)
        
        assert result['title'] == 'Manual Title'  # Manual
        assert result['tags'] == ['Action', 'tag1']  # Layer 1


# =============================================================================
# Generate Title Layer 1 Tests
# =============================================================================

class TestGenerateTitleLayer1:
    """Tests for generate_title_layer1 function."""
    
    def test_generate_title_with_steam(self):
        """Test returns non-empty string containing game name."""
        short = {'name': 'eic_short_1_evolution', 'beats': []}
        steam = {'name': 'Everything is Crab', 'description': '', 'genres': [], 'tags': []}
        
        result = generate_title_layer1(short, steam)
        
        assert result != ''
        assert 'Everything is Crab' in result
        assert 'Eic Short 1 Evolution' in result
    
    def test_generate_title_without_steam(self):
        """Test returns non-empty string when steam is None."""
        short = {'name': 'eic_short_1_evolution', 'beats': []}
        
        result = generate_title_layer1(short, None)
        
        assert result != ''
        assert 'Eic Short 1 Evolution' in result


# =============================================================================
# Generate Description Layer 1 Tests
# =============================================================================

class TestGenerateDescriptionLayer1:
    """Tests for generate_description_layer1 function."""
    
    def test_generate_description_layer1(self):
        """Test returns non-empty string, does not exceed 5000 chars."""
        short = {'name': 'eic_short_1', 'beats': [{'clip_start': '0:00', 'clip_end': '0:10', 'duration': 10, 'line': 'Test'}]}
        steam = {'name': 'Game', 'description': 'A' * 4000, 'genres': [], 'tags': []}
        
        result = generate_description_layer1(short, steam)
        
        assert result != ''
        assert len(result) <= 5000
        assert '1 segments' in result


# =============================================================================
# Generate Tags Layer 1 Tests
# =============================================================================

class TestGenerateTagsLayer1:
    """Tests for generate_tags_layer1 function."""
    
    def test_generate_tags_enforces_500_char_limit(self):
        """Test total tag string length never exceeds 500 chars."""
        short = {'name': 'eic_short_1', 'beats': []}
        steam = {
            'name': 'Game',
            'description': '',
            'genres': ['A' * 100, 'B' * 100, 'C' * 100],
            'tags': ['D' * 100, 'E' * 100, 'F' * 100]
        }
        
        result = generate_tags_layer1(short, steam)
        
        tags_string = ','.join(str(t) for t in result)
        assert len(tags_string) <= 500


# =============================================================================
# Validate Metadata Tests
# =============================================================================

class TestValidateMetadata:
    """Tests for validate_metadata function."""
    
    def test_validate_title_too_long(self):
        """Test title > 100 chars returns error."""
        metadata = {
            'title': 'A' * 101,
            'description': '',
            'tags': [],
            'privacy': 'public'
        }
        
        errors = validate_metadata(metadata)
        
        assert len(errors) > 0
        assert any('Title exceeds 100 characters' in e for e in errors)
    
    def test_validate_empty_title(self):
        """Test empty title returns error."""
        metadata = {
            'title': '',
            'description': '',
            'tags': [],
            'privacy': 'public'
        }
        
        errors = validate_metadata(metadata)
        
        assert len(errors) > 0
        assert any('Title cannot be empty' in e for e in errors)
    
    def test_validate_tags_too_long(self):
        """Test tags > 500 chars total returns error."""
        metadata = {
            'title': 'Valid Title',
            'description': '',
            'tags': ['A' * 501],
            'privacy': 'public'
        }
        
        errors = validate_metadata(metadata)
        
        assert len(errors) > 0
        assert any('Tags exceed 500 characters' in e for e in errors)
    
    def test_validate_invalid_privacy(self):
        """Test invalid privacy value returns error."""
        metadata = {
            'title': 'Valid Title',
            'description': '',
            'tags': [],
            'privacy': 'invalid'
        }
        
        errors = validate_metadata(metadata)
        
        assert len(errors) > 0
        assert any('Invalid privacy value' in e for e in errors)
    
    def test_validate_clean_metadata(self):
        """Test valid metadata returns empty list."""
        metadata = {
            'title': 'Valid Title',
            'description': 'Valid description',
            'tags': ['tag1', 'tag2'],
            'privacy': 'public'
        }
        
        errors = validate_metadata(metadata)
        
        assert errors == []


# =============================================================================
# Format Schedule Tests
# =============================================================================

class TestFormatSchedule:
    """Tests for format_schedule function."""
    
    def test_format_schedule_empty(self):
        """Test empty string returns None."""
        result = format_schedule('')
        
        assert result is None
    
    def test_format_schedule_valid(self):
        """Test valid datetime string returns RFC 3339 format."""
        result = format_schedule('2026-05-23T21:00:00')
        
        assert result is not None
        assert 'T' in result  # RFC 3339 format
        assert '2026-05-23' in result
    
    def test_format_schedule_invalid(self):
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError):
            format_schedule('invalid-date')
