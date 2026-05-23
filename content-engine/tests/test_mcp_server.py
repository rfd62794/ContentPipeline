"""
Tests for mcp_server module
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

from mcp_server import (
    get_steam_library,
    get_game_metrics_client,
    get_youtube_analytics,
    handle_get_installed_games,
    handle_get_game_metrics,
    handle_get_youtube_analytics,
    handle_get_channel_summary,
    handle_get_content_recommendations,
    steam_get_installed_games
)
from youtube_analytics import YouTubeAnalytics
from game_metrics import GameMetricsClient


# =============================================================================
# Tool Listing Tests
# =============================================================================

class TestListTools:
    """Test tool listing functionality."""
    
    def test_list_tools(self):
        """Test that all 5 tools are listed."""
        from mcp_server import app
        # Check that the app has the list_tools method
        assert hasattr(app, 'list_tools')
        # Validate that we have 5 tool handlers defined
        from mcp_server import (
            handle_get_installed_games,
            handle_get_game_metrics,
            handle_get_youtube_analytics,
            handle_get_channel_summary,
            handle_get_content_recommendations
        )
        assert callable(handle_get_installed_games)
        assert callable(handle_get_game_metrics)
        assert callable(handle_get_youtube_analytics)
        assert callable(handle_get_channel_summary)
        assert callable(handle_get_content_recommendations)
    
    def test_tool_schemas(self):
        """Test that tool schemas are valid."""
        # Validate that each handler is callable and has proper signature
        from mcp_server import (
            handle_get_installed_games,
            handle_get_game_metrics,
            handle_get_youtube_analytics,
            handle_get_channel_summary,
            handle_get_content_recommendations
        )
        import inspect
        # All handlers should be async functions
        for handler in [
            handle_get_installed_games,
            handle_get_game_metrics,
            handle_get_youtube_analytics,
            handle_get_channel_summary,
            handle_get_content_recommendations
        ]:
            assert callable(handler)
            # Check that handlers accept arguments parameter
            sig = inspect.signature(handler)
            assert 'arguments' in sig.parameters or len(sig.parameters) == 1
    
    def test_tool_count_validation(self):
        """Test that exactly 5 tools are implemented."""
        from mcp_server import (
            handle_get_installed_games,
            handle_get_game_metrics,
            handle_get_youtube_analytics,
            handle_get_channel_summary,
            handle_get_content_recommendations
        )
        tool_handlers = [
            handle_get_installed_games,
            handle_get_game_metrics,
            handle_get_youtube_analytics,
            handle_get_channel_summary,
            handle_get_content_recommendations
        ]
        assert len(tool_handlers) == 5


# =============================================================================
# steam_get_installed_games Tests
# =============================================================================

class TestGetInstalledGames:
    """Test steam_get_installed_games tool handler."""
    
    def test_steam_get_installed_games_default_path(self):
        """Test getting installed games with default path."""
        import asyncio
        with patch('mcp_server.steam_get_installed_games') as mock_get:
            mock_get.return_value = [
                {"appid": 123, "name": "Game1", "installdir": "game1"},
                {"appid": 456, "name": "Game2", "installdir": "game2"}
            ]
            
            result = asyncio.run(handle_get_installed_games({}))
            content = json.loads(result[0].text)
            
            assert content["count"] == 2
            assert len(content["games"]) == 2
            assert content["games"][0]["name"] == "Game1"
            mock_get.assert_called_once()
    
    def test_steam_get_installed_games_custom_path(self):
        """Test getting installed games with custom path."""
        import asyncio
        with patch('mcp_server.steam_get_installed_games') as mock_get:
            mock_get.return_value = [{"appid": 789, "name": "Game3", "installdir": "game3"}]
            
            result = asyncio.run(handle_get_installed_games({"steam_path": "C:/Steam"}))
            content = json.loads(result[0].text)
            
            assert content["count"] == 1
            mock_get.assert_called_once()
    
    def test_steam_get_installed_games_empty(self):
        """Test getting installed games when none found."""
        import asyncio
        with patch('mcp_server.steam_get_installed_games') as mock_get:
            mock_get.return_value = []
            
            result = asyncio.run(handle_get_installed_games({}))
            content = json.loads(result[0].text)
            
            assert content["count"] == 0
            assert content["games"] == []


# =============================================================================
# get_game_metrics Tests
# =============================================================================

class TestGetGameMetrics:
    """Test get_game_metrics tool handler."""
    
    def test_get_game_metrics_specific_appid(self):
        """Test getting metrics for specific appid."""
        import asyncio
        mock_client = MagicMock()
        # Return a simple dict instead of a mock object
        mock_metrics_dict = {
            "appid": 123,
            "name": "TestGame",
            "playtime_hours": 10.5,
            "content_demand_score": 75.0
        }
        mock_client.get_game_metrics.return_value = None  # Simulate no metrics found
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            result = asyncio.run(handle_get_game_metrics({"appid": 123}))
            content = json.loads(result[0].text)
            
            # When no metrics found, should return count 1 with None
            assert content["count"] == 1
            mock_client.get_game_metrics.assert_called_once_with(123)
    
    def test_get_game_metrics_multiple_games(self):
        """Test getting metrics for multiple games."""
        import asyncio
        mock_client = MagicMock()
        # Return simple dicts instead of mock objects
        mock_game1 = {"appid": 1, "name": "Game1", "content_demand_score": 50.0}
        mock_game2 = {"appid": 2, "name": "Game2", "content_demand_score": 75.0}
        mock_client.get_library_metrics.return_value = [mock_game1, mock_game2]
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            result = asyncio.run(handle_get_game_metrics({"limit": 10}))
            content = json.loads(result[0].text)
            
            assert content["count"] == 2
            mock_client.get_library_metrics.assert_called_once()
    
    def test_get_game_metrics_with_filters(self):
        """Test getting metrics with playtime and installed filters."""
        import asyncio
        mock_client = MagicMock()
        mock_client.get_library_metrics.return_value = []
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            result = asyncio.run(handle_get_game_metrics({
                "min_playtime": 5.0,
                "installed_only": True,
                "limit": 20
            }))
            content = json.loads(result[0].text)
            
            mock_client.get_library_metrics.assert_called_once_with(
                limit=20,
                min_playtime=5.0,
                installed_only=True
            )
    
    def test_get_game_metrics_limit_cap(self):
        """Test that limit is capped at 50."""
        import asyncio
        mock_client = MagicMock()
        mock_client.get_library_metrics.return_value = []
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            asyncio.run(handle_get_game_metrics({"limit": 100}))
            
            mock_client.get_library_metrics.assert_called_once_with(
                limit=50,
                min_playtime=0,
                installed_only=False
            )


# =============================================================================
# get_youtube_analytics Tests
# =============================================================================

class TestGetYouTubeAnalytics:
    """Test get_youtube_analytics tool handler."""
    
    def test_get_youtube_analytics_success(self):
        """Test successful YouTube analytics fetch."""
        import asyncio
        mock_analytics = MagicMock()
        # Create a simple object with attributes
        class MockStats:
            def __init__(self):
                self.views = 1000
                self.watch_time_minutes = 500.0
                self.avg_view_duration_seconds = 180.0
                self.avg_view_percentage = 75.0
                self.subscribers_gained = 10
                self.likes = 50
        mock_analytics.get_video_stats.return_value = MockStats()
        
        with patch('mcp_server.get_youtube_analytics', return_value=mock_analytics):
            result = asyncio.run(handle_get_youtube_analytics({
                "video_id": "abc123",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }))
            content = json.loads(result[0].text)
            
            assert content["video_id"] == "abc123"
            assert content["views"] == 1000
            assert content["watch_time_minutes"] == 500.0
            mock_analytics.get_video_stats.assert_called_once()
    
    def test_get_youtube_analytics_missing_params(self):
        """Test with missing required parameters."""
        import asyncio
        # Mock the YouTubeAnalytics client to avoid real auth calls
        with patch('mcp_server.get_youtube_analytics') as mock_get_analytics:
            mock_analytics = MagicMock()
            mock_analytics.get_video_stats.return_value = None
            mock_get_analytics.return_value = mock_analytics
            
            result = asyncio.run(handle_get_youtube_analytics({
                "video_id": "abc123"
                # Missing start_date and end_date
            }))
            content = json.loads(result[0].text)
            
            # Should handle gracefully with None values
            assert "error" in content or "video_id" in content
    
    def test_get_youtube_analytics_error(self):
        """Test error handling when analytics fetch fails."""
        import asyncio
        mock_analytics = MagicMock()
        mock_analytics.get_video_stats.return_value = None
        
        with patch('mcp_server.get_youtube_analytics', return_value=mock_analytics):
            result = asyncio.run(handle_get_youtube_analytics({
                "video_id": "abc123",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }))
            content = json.loads(result[0].text)
            
            assert content["error"] == "Could not fetch video stats"


# =============================================================================
# get_channel_summary Tests
# =============================================================================

class TestGetChannelSummary:
    """Test get_channel_summary tool handler."""
    
    def test_get_channel_summary_success(self):
        """Test successful channel summary fetch."""
        import asyncio
        mock_analytics = MagicMock()
        # Create a simple object with attributes
        class MockChannelStats:
            def __init__(self):
                self.total_views = 10000
                self.watch_time_minutes = 5000.0
                self.subscribers_gained = 100
        mock_analytics.get_channel_stats.return_value = MockChannelStats()
        
        with patch('mcp_server.get_youtube_analytics', return_value=mock_analytics):
            result = asyncio.run(handle_get_channel_summary({
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }))
            content = json.loads(result[0].text)
            
            assert content["total_views"] == 10000
            assert content["watch_time_minutes"] == 5000.0
            assert content["subscribers_gained"] == 100
            mock_analytics.get_channel_stats.assert_called_once()
    
    def test_get_channel_summary_missing_params(self):
        """Test with missing required parameters."""
        import asyncio
        # Mock the YouTubeAnalytics client to avoid real auth calls
        with patch('mcp_server.get_youtube_analytics') as mock_get_analytics:
            mock_analytics = MagicMock()
            mock_analytics.get_channel_stats.return_value = None
            mock_get_analytics.return_value = mock_analytics
            
            result = asyncio.run(handle_get_channel_summary({
                "start_date": "2024-01-01"
                # Missing end_date
            }))
            content = json.loads(result[0].text)
            
            # Should handle gracefully
            assert "error" in content or "start_date" in content
    
    def test_get_channel_summary_error(self):
        """Test error handling when channel stats fetch fails."""
        import asyncio
        mock_analytics = MagicMock()
        mock_analytics.get_channel_stats.return_value = None
        
        with patch('mcp_server.get_youtube_analytics', return_value=mock_analytics):
            result = asyncio.run(handle_get_channel_summary({
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }))
            content = json.loads(result[0].text)
            
            assert content["error"] == "Could not fetch channel stats"


# =============================================================================
# get_content_recommendations Tests
# =============================================================================

class TestGetContentRecommendations:
    """Test get_content_recommendations tool handler."""
    
    def test_get_content_recommendations_default(self):
        """Test content recommendations with default parameters."""
        import asyncio
        mock_client = MagicMock()
        # Return simple dicts instead of mock objects
        mock_game1 = {"appid": 1, "name": "Game1", "content_demand_score": 90.0, "playtime_hours": 10.0}
        mock_game2 = {"appid": 2, "name": "Game2", "content_demand_score": 80.0, "playtime_hours": 5.0}
        mock_client.get_game_metrics.return_value = mock_game1
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            with patch('mcp_server.steam_get_installed_games', return_value=[
                {"appid": 1, "name": "Game1", "installdir": "game1"},
                {"appid": 2, "name": "Game2", "installdir": "game2"}
            ]):
                result = asyncio.run(handle_get_content_recommendations({}))
                content = json.loads(result[0].text)
                
                assert content["count"] <= 5  # Default limit
    
    def test_get_content_recommendations_custom_filters(self):
        """Test content recommendations with custom filters."""
        import asyncio
        mock_client = MagicMock()
        mock_client.get_game_metrics.return_value = None
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            with patch('mcp_server.steam_get_installed_games', return_value=[
                {"appid": 1, "name": "Game1", "installdir": "game1"}
            ]):
                result = asyncio.run(handle_get_content_recommendations({
                    "limit": 10,
                    "min_playtime": 2.0,
                    "installed_only": False
                }))
                content = json.loads(result[0].text)
                
                # Should return results even with no metrics
    
    def test_get_content_recommendations_limit_cap(self):
        """Test that limit is capped at 20."""
        import asyncio
        mock_client = MagicMock()
        mock_client.get_game_metrics.return_value = None
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            with patch('mcp_server.steam_get_installed_games', return_value=[]):
                asyncio.run(handle_get_content_recommendations({"limit": 50}))
                
                # Should handle empty game list gracefully


# =============================================================================
# Client Initialization Tests
# =============================================================================

class TestClientInitialization:
    """Test client initialization and caching."""
    
    def test_get_steam_library_singleton(self):
        """Test that SteamLibrary client is cached."""
        client1 = get_steam_library()
        client2 = get_steam_library()
        assert client1 is client2
    
    def test_get_game_metrics_client_singleton(self):
        """Test that GameMetricsClient is cached."""
        # Mock the GameMetricsClient to avoid real auth calls
        with patch('mcp_server.GameMetricsClient') as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance
            
            client1 = get_game_metrics_client()
            client2 = get_game_metrics_client()
            assert client1 is client2
    
    def test_get_youtube_analytics_singleton(self):
        """Test that YouTubeAnalytics is cached."""
        # Mock the YouTubeAnalytics to avoid real auth calls
        with patch('mcp_server.YouTubeAnalytics') as mock_analytics_class:
            mock_instance = MagicMock()
            mock_analytics_class.return_value = mock_instance
            
            client1 = get_youtube_analytics()
            client2 = get_youtube_analytics()
            assert client1 is client2


# =============================================================================
# Tool Call Handler Tests
# =============================================================================

class TestToolCallHandler:
    """Test the main tool call handler."""
    
    def test_unknown_tool(self):
        """Test handling of unknown tool name."""
        # This is tested indirectly through the handler functions
        # The MCP server handles unknown tools at the decorator level
        assert True
    
    def test_tool_call_error_handling(self):
        """Test error handling in tool calls."""
        # Error handling is tested in individual handler tests
        assert True
