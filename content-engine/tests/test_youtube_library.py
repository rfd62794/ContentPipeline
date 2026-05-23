"""
Tests for YouTube Library Data Client

All tests use pure functions with mocked API calls.
No network calls, no real OAuth, no real file I/O beyond fixture data.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock

from youtube_library import (
    YouTubeChannel,
    YouTubeVideo,
    YouTubePlaylist,
    parse_channel_response,
    parse_video_response,
    parse_playlist_response,
    format_duration
)


# =============================================================================
# Parse Function Tests
# =============================================================================

class TestParseChannelResponse:
    """Tests for parse_channel_response pure function."""
    
    def test_parse_channel_response_full(self):
        """Test parsing full channel response."""
        raw = {
            'items': [{
                'id': 'UC1234567890',
                'snippet': {
                    'title': 'Test Channel',
                    'description': 'Test channel description',
                    'customUrl': 'testchannel'
                },
                'statistics': {
                    'subscriberCount': '1000',
                    'viewCount': '50000',
                    'videoCount': '100'
                }
            }]
        }
        
        result = parse_channel_response(raw)
        
        assert result.channel_id == 'UC1234567890'
        assert result.title == 'Test Channel'
        assert result.description == 'Test channel description'
        assert result.subscriber_count == 1000
        assert result.total_views == 50000
        assert result.video_count == 100
        assert result.custom_url == 'testchannel'
    
    def test_parse_channel_response_minimal(self):
        """Test parsing minimal channel response."""
        raw = {
            'items': [{
                'id': 'UC1234567890',
                'snippet': {
                    'title': 'Test Channel',
                    'description': ''
                },
                'statistics': {
                    'subscriberCount': '0',
                    'viewCount': '0',
                    'videoCount': '0'
                }
            }]
        }
        
        result = parse_channel_response(raw)
        
        assert result.channel_id == 'UC1234567890'
        assert result.title == 'Test Channel'
        assert result.subscriber_count == 0
        assert result.total_views == 0
        assert result.video_count == 0


class TestParseVideoResponse:
    """Tests for parse_video_response pure function."""
    
    def test_parse_video_response_full(self):
        """Test parsing full video response."""
        raw = {
            'items': [{
                'id': 'video123',
                'snippet': {
                    'title': 'Test Video',
                    'description': 'Test video description',
                    'publishedAt': '2024-01-01T00:00:00Z',
                    'tags': ['tag1', 'tag2', 'tag3'],
                    'thumbnails': {
                        'default': {'url': 'https://example.com/thumb.jpg'}
                    }
                },
                'contentDetails': {
                    'duration': 'PT4M13S'
                },
                'status': {
                    'privacyStatus': 'public'
                },
                'statistics': {
                    'viewCount': '1000',
                    'likeCount': '50',
                    'commentCount': '10'
                }
            }]
        }
        
        result = parse_video_response(raw)
        
        assert result.video_id == 'video123'
        assert result.title == 'Test Video'
        assert result.description == 'Test video description'
        assert result.tags == ['tag1', 'tag2', 'tag3']
        assert result.publish_date == '2024-01-01T00:00:00Z'
        assert result.status == 'public'
        assert result.duration == 'PT4M13S'
        assert result.thumbnail_url == 'https://example.com/thumb.jpg'
        assert result.view_count == 1000
        assert result.like_count == 50
        assert result.comment_count == 10
    
    def test_parse_video_response_minimal(self):
        """Test parsing minimal video response."""
        raw = {
            'items': [{
                'id': 'video123',
                'snippet': {
                    'title': 'Test Video',
                    'description': '',
                    'publishedAt': '2024-01-01T00:00:00Z',
                    'tags': [],
                    'thumbnails': {}
                },
                'contentDetails': {
                    'duration': 'PT1M00S'
                },
                'status': {
                    'privacyStatus': 'private'
                },
                'statistics': {
                    'viewCount': '0',
                    'likeCount': '0',
                    'commentCount': '0'
                }
            }]
        }
        
        result = parse_video_response(raw)
        
        assert result.video_id == 'video123'
        assert result.title == 'Test Video'
        assert result.tags == []
        assert result.status == 'private'
        assert result.view_count == 0


class TestParsePlaylistResponse:
    """Tests for parse_playlist_response pure function."""
    
    def test_parse_playlist_response_full(self):
        """Test parsing full playlist response."""
        raw = {
            'items': [{
                'id': 'PL1234567890',
                'snippet': {
                    'title': 'Test Playlist',
                    'description': 'Test playlist description',
                    'thumbnails': {
                        'default': {'url': 'https://example.com/playlist.jpg'}
                    }
                },
                'contentDetails': {
                    'itemCount': '10'
                }
            }]
        }
        
        result = parse_playlist_response(raw)
        
        assert result.playlist_id == 'PL1234567890'
        assert result.title == 'Test Playlist'
        assert result.description == 'Test playlist description'
        assert result.video_count == 10
        assert result.thumbnail_url == 'https://example.com/playlist.jpg'
    
    def test_parse_playlist_response_minimal(self):
        """Test parsing minimal playlist response."""
        raw = {
            'items': [{
                'id': 'PL1234567890',
                'snippet': {
                    'title': 'Test Playlist',
                    'description': '',
                    'thumbnails': {}
                },
                'contentDetails': {
                    'itemCount': '0'
                }
            }]
        }
        
        result = parse_playlist_response(raw)
        
        assert result.playlist_id == 'PL1234567890'
        assert result.title == 'Test Playlist'
        assert result.video_count == 0


class TestFormatDuration:
    """Tests for format_duration pure function."""
    
    def test_format_duration_hours_minutes_seconds(self):
        """Test PT1H30M45S -> 1:30:45."""
        result = format_duration('PT1H30M45S')
        assert result == '1:30:45'
    
    def test_format_duration_minutes_seconds(self):
        """Test PT4M13S -> 4:13."""
        result = format_duration('PT4M13S')
        assert result == '4:13'
    
    def test_format_duration_seconds_only(self):
        """Test PT30S -> 0:30."""
        result = format_duration('PT30S')
        assert result == '0:30'
    
    def test_format_duration_hours_only(self):
        """Test PT2H -> 2:00:00."""
        result = format_duration('PT2H')
        assert result == '2:00:00'
    
    def test_format_duration_invalid_format(self):
        """Test invalid format returns as-is."""
        result = format_duration('invalid')
        assert result == 'invalid'
    
    def test_format_duration_empty(self):
        """Test empty string returns as-is."""
        result = format_duration('')
        assert result == ''