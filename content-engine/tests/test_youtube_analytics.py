"""
Tests for YouTube Analytics Client

All tests use pure functions with mocked API calls.
No network calls, no real OAuth, no real file I/O beyond fixture data.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from youtube_analytics import (
    VideoStats,
    RetentionPoint,
    ChannelStats,
    parse_stats_response,
    parse_retention_response,
    parse_traffic_response,
    format_retention_curve
)


# =============================================================================
# Parse Function Tests
# =============================================================================

class TestParseStatsResponse:
    """Tests for parse_stats_response pure function."""
    
    def test_parse_stats_response_full(self):
        """Test parsing full stats response."""
        raw = {
            'rows': [
                [1000, 5000.5, 180.0, 45.0, 50, 100]
            ]
        }
        
        result = parse_stats_response(raw)
        
        assert result['views'] == 1000
        assert result['watch_time_minutes'] == 5000.5
        assert result['avg_view_duration_seconds'] == 180.0
        assert result['avg_view_percentage'] == 45.0
        assert result['subscribers_gained'] == 50
        assert result['likes'] == 100
    
    def test_parse_stats_response_empty(self):
        """Test parsing empty stats response."""
        raw = {'rows': []}
        
        result = parse_stats_response(raw)
        
        assert result == {}


class TestParseRetentionResponse:
    """Tests for parse_retention_response pure function."""
    
    def test_parse_retention_response_full(self):
        """Test parsing full retention response."""
        raw = {
            'rows': [
                [0.0, 1.0],
                [0.5, 0.8],
                [1.0, 0.6]
            ]
        }
        
        result = parse_retention_response(raw)
        
        assert len(result) == 3
        assert result[0] == (0.0, 1.0)
        assert result[1] == (0.5, 0.8)
        assert result[2] == (1.0, 0.6)
    
    def test_parse_retention_response_empty(self):
        """Test parsing empty retention response."""
        raw = {'rows': []}
        
        result = parse_retention_response(raw)
        
        assert result == []


class TestParseTrafficResponse:
    """Tests for parse_traffic_response pure function."""
    
    def test_parse_traffic_response_full(self):
        """Test parsing full traffic response."""
        raw = {
            'rows': [
                ['youtube_search', 500],
                ['browse', 300],
                ['external', 200]
            ]
        }
        
        result = parse_traffic_response(raw)
        
        assert result['youtube_search'] == 500
        assert result['browse'] == 300
        assert result['external'] == 200
    
    def test_parse_traffic_response_empty(self):
        """Test parsing empty traffic response."""
        raw = {'rows': []}
        
        result = parse_traffic_response(raw)
        
        assert result == {}


class TestFormatRetentionCurve:
    """Tests for format_retention_curve pure function."""
    
    def test_format_retention_curve_full(self):
        """Test formatting full retention curve."""
        points = [
            (0.0, 1.0),
            (0.5, 0.8),
            (1.0, 0.6)
        ]
        
        result = format_retention_curve(points, width=50)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_format_retention_curve_empty(self):
        """Test formatting empty retention curve."""
        points = []
        
        result = format_retention_curve(points)
        
        assert result == "No retention data available"
    
    def test_format_retention_curve_custom_width(self):
        """Test formatting with custom width."""
        points = [(0.0, 1.0), (1.0, 0.5)]
        
        result = format_retention_curve(points, width=20)
        
        assert isinstance(result, str)
        assert len(result) <= 20 * 10  # Max 10 lines per position


class TestVideoStats:
    """Tests for VideoStats dataclass."""
    
    def test_video_stats_creation(self):
        """Test VideoStats dataclass creation."""
        stats = VideoStats(
            video_id='abc123',
            views=1000,
            watch_time_minutes=5000.5,
            avg_view_duration_seconds=180.0,
            avg_view_percentage=45.0,
            subscribers_gained=50,
            likes=100,
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        assert stats.video_id == 'abc123'
        assert stats.views == 1000
        assert stats.avg_view_percentage == 45.0


class TestRetentionPoint:
    """Tests for RetentionPoint dataclass."""
    
    def test_retention_point_creation(self):
        """Test RetentionPoint dataclass creation."""
        point = RetentionPoint(
            elapsed_video_time_ratio=0.5,
            audience_watch_ratio=0.8
        )
        
        assert point.elapsed_video_time_ratio == 0.5
        assert point.audience_watch_ratio == 0.8


class TestChannelStats:
    """Tests for ChannelStats dataclass."""
    
    def test_channel_stats_creation(self):
        """Test ChannelStats dataclass creation."""
        stats = ChannelStats(
            total_views=10000,
            watch_time_minutes=50000.0,
            subscribers_gained=100,
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        assert stats.total_views == 10000
        assert stats.subscribers_gained == 100


class TestCLIInterface:
    """Tests for CLI interface functions."""
    
    def test_format_retention_curve_various_heights(self):
        """Test retention curve with various audience percentages."""
        points = [
            (0.0, 1.0),   # 100% - 10 chars
            (0.25, 0.5),  # 50% - 5 chars
            (0.5, 0.3),   # 30% - 3 chars
            (0.75, 0.1),  # 10% - 1 char
            (1.0, 0.05)   # 5% - 0 chars
        ]
        
        result = format_retention_curve(points, width=50)
        
        assert isinstance(result, str)
        assert '█' in result  # Should have some blocks
    
    def test_format_retention_curve_zero_audience(self):
        """Test retention curve with zero audience."""
        points = [
            (0.0, 0.0),
            (0.5, 0.0),
            (1.0, 0.0)
        ]
        
        result = format_retention_curve(points)
        
        assert isinstance(result, str)
        # Should have spaces but no blocks since audience is 0
    
    def test_format_retention_curve_max_audience(self):
        """Test retention curve with max audience."""
        points = [
            (0.0, 1.0),
            (0.5, 1.0),
            (1.0, 1.0)
        ]
        
        result = format_retention_curve(points, width=10)
        
        assert isinstance(result, str)
        assert '█' in result  # Should have blocks
    
    def test_parse_stats_response_large_numbers(self):
        """Test parsing stats with large numbers."""
        raw = {
            'rows': [
                [1000000, 5000000.0, 300.0, 50.0, 1000, 50000]
            ]
        }
        
        result = parse_stats_response(raw)
        
        assert result['views'] == 1000000
        assert result['watch_time_minutes'] == 5000000.0
        assert result['likes'] == 50000
    
    def test_parse_traffic_response_single_source(self):
        """Test parsing traffic response with single source."""
        raw = {
            'rows': [
                ['youtube_search', 1000]
            ]
        }
        
        result = parse_traffic_response(raw)
        
        assert len(result) == 1
        assert result['youtube_search'] == 1000
    
    def test_parse_retention_response_single_point(self):
        """Test parsing retention response with single point."""
        raw = {
            'rows': [
                [0.0, 1.0]
            ]
        }
        
        result = parse_retention_response(raw)
        
        assert len(result) == 1
        assert result[0] == (0.0, 1.0)
    
    def test_parse_stats_response_zero_values(self):
        """Test parsing stats with zero values."""
        raw = {
            'rows': [
                [0, 0.0, 0.0, 0.0, 0, 0]
            ]
        }
        
        result = parse_stats_response(raw)
        
        assert result['views'] == 0
        assert result['watch_time_minutes'] == 0.0
        assert result['subscribers_gained'] == 0
    
    def test_format_retention_curve_narrow_width(self):
        """Test formatting with narrow width."""
        points = [(0.0, 1.0), (0.5, 0.8), (1.0, 0.6)]
        
        result = format_retention_curve(points, width=5)
        
        assert isinstance(result, str)
        # Should be shorter due to narrow width
    
    def test_parse_traffic_response_many_sources(self):
        """Test parsing traffic response with many sources."""
        raw = {
            'rows': [
                ['source1', 100],
                ['source2', 200],
                ['source3', 300],
                ['source4', 400],
                ['source5', 500]
            ]
        }
        
        result = parse_traffic_response(raw)
        
        assert len(result) == 5
        assert result['source5'] == 500
    
    def test_parse_stats_response_negative_subscribers(self):
        """Test parsing stats with negative subscriber change."""
        raw = {
            'rows': [
                [1000, 5000.0, 180.0, 45.0, -10, 100]
            ]
        }
        
        result = parse_stats_response(raw)
        
        assert result['subscribers_gained'] == -10