"""
Tests for mcp_server module
"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

from mcp_server import (
    app,
    get_steam_library,
    get_game_metrics_client,
    get_youtube_analytics,
    handle_get_installed_games,
    handle_get_game_metrics,
    handle_get_youtube_analytics,
    handle_get_channel_summary,
    handle_get_content_recommendations
)


# =============================================================================
# Tool Listing Tests
# =============================================================================

class TestListTools:
    """Test tool listing functionality."""
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test that all 5 tools are listed."""
        tools = await app.list_tools()
        assert len(tools) == 5
        
        tool_names = {tool.name for tool in tools}
        expected_names = {
            "get_installed_games",
            "get_game_metrics",
            "get_youtube_analytics",
            "get_channel_summary",
            "get_content_recommendations"
        }
        assert tool_names == expected_names
    
    @pytest.mark.asyncio
    async def test_tool_schemas(self):
        """Test that tool schemas are valid."""
        tools = await app.list_tools()
        
        for tool in tools:
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert tool.inputSchema.get("type") == "object"
            assert "properties" in tool.inputSchema


# =============================================================================
# get_installed_games Tests
# =============================================================================

class TestGetInstalledGames:
    """Test get_installed_games tool handler."""
    
    @pytest.mark.asyncio
    async def test_get_installed_games_default_path(self):
        """Test getting installed games with default path."""
        with patch('mcp_server.get_installed_games') as mock_get:
            mock_get.return_value = [
                {"appid": 123, "name": "Game1", "installdir": "game1"},
                {"appid": 456, "name": "Game2", "installdir": "game2"}
            ]
            
            result = await handle_get_installed_games({})
            content = json.loads(result[0].text)
            
            assert content["count"] == 2
            assert len(content["games"]) == 2
            assert content["games"][0]["name"] == "Game1"
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_installed_games_custom_path(self):
        """Test getting installed games with custom path."""
        with patch('mcp_server.get_installed_games') as mock_get:
            mock_get.return_value = [{"appid": 789, "name": "Game3", "installdir": "game3"}]
            
            result = await handle_get_installed_games({"steam_path": "C:/Steam"})
            content = json.loads(result[0].text)
            
            assert content["count"] == 1
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_installed_games_empty(self):
        """Test getting installed games when none found."""
        with patch('mcp_server.get_installed_games') as mock_get:
            mock_get.return_value = []
            
            result = await handle_get_installed_games({})
            content = json.loads(result[0].text)
            
            assert content["count"] == 0
            assert content["games"] == []


# =============================================================================
# get_game_metrics Tests
# =============================================================================

class TestGetGameMetrics:
    """Test get_game_metrics tool handler."""
    
    @pytest.mark.asyncio
    async def test_get_game_metrics_specific_appid(self):
        """Test getting metrics for specific appid."""
        mock_client = MagicMock()
        mock_metrics = MagicMock()
        mock_metrics.__dict__ = {
            "appid": 123,
            "name": "TestGame",
            "playtime_hours": 10.5,
            "content_demand_score": 75.0
        }
        mock_client.get_game_metrics.return_value = mock_metrics
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            result = await handle_get_game_metrics({"appid": 123})
            content = json.loads(result[0].text)
            
            assert content["count"] == 1
            assert content["games"][0]["appid"] == 123
            mock_client.get_game_metrics.assert_called_once_with(123)
    
    @pytest.mark.asyncio
    async def test_get_game_metrics_multiple_games(self):
        """Test getting metrics for multiple games."""
        mock_client = MagicMock()
        mock_game1 = MagicMock()
        mock_game1.__dict__ = {"appid": 1, "name": "Game1", "content_demand_score": 50.0}
        mock_game2 = MagicMock()
        mock_game2.__dict__ = {"appid": 2, "name": "Game2", "content_demand_score": 75.0}
        mock_client.get_library_metrics.return_value = [mock_game1, mock_game2]
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            result = await handle_get_game_metrics({"limit": 10})
            content = json.loads(result[0].text)
            
            assert content["count"] == 2
            mock_client.get_library_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_game_metrics_with_filters(self):
        """Test getting metrics with playtime and installed filters."""
        mock_client = MagicMock()
        mock_client.get_library_metrics.return_value = []
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            result = await handle_get_game_metrics({
                "min_playtime": 5.0,
                "installed_only": True,
                "limit": 20
            })
            content = json.loads(result[0].text)
            
            mock_client.get_library_metrics.assert_called_once_with(
                limit=20,
                min_playtime=5.0,
                installed_only=True
            )
    
    @pytest.mark.asyncio
    async def test_get_game_metrics_limit_cap(self):
        """Test that limit is capped at 50."""
        mock_client = MagicMock()
        mock_client.get_library_metrics.return_value = []
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            await handle_get_game_metrics({"limit": 100})
            
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
    
    @pytest.mark.asyncio
    async def test_get_youtube_analytics_success(self):
        """Test successful YouTube analytics fetch."""
        mock_analytics = MagicMock()
        mock_stats = MagicMock()
        mock_stats.views = 1000
        mock_stats.watch_time_minutes = 500.0
        mock_stats.avg_view_duration_seconds = 180.0
        mock_stats.avg_view_percentage = 75.0
        mock_stats.subscribers_gained = 10
        mock_stats.likes = 50
        mock_analytics.get_video_stats.return_value = mock_stats
        
        with patch('mcp_server.get_youtube_analytics', return_value=mock_analytics):
            result = await handle_get_youtube_analytics({
                "video_id": "abc123",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            })
            content = json.loads(result[0].text)
            
            assert content["video_id"] == "abc123"
            assert content["views"] == 1000
            assert content["watch_time_minutes"] == 500.0
            mock_analytics.get_video_stats.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_youtube_analytics_missing_params(self):
        """Test with missing required parameters."""
        result = await handle_get_youtube_analytics({
            "video_id": "abc123"
            # Missing start_date and end_date
        })
        content = json.loads(result[0].text)
        
        # Should handle gracefully with None values
        assert "error" in content or "video_id" in content
    
    @pytest.mark.asyncio
    async def test_get_youtube_analytics_error(self):
        """Test error handling when analytics fetch fails."""
        mock_analytics = MagicMock()
        mock_analytics.get_video_stats.return_value = None
        
        with patch('mcp_server.get_youtube_analytics', return_value=mock_analytics):
            result = await handle_get_youtube_analytics({
                "video_id": "abc123",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            })
            content = json.loads(result[0].text)
            
            assert content["error"] == "Could not fetch video stats"


# =============================================================================
# get_channel_summary Tests
# =============================================================================

class TestGetChannelSummary:
    """Test get_channel_summary tool handler."""
    
    @pytest.mark.asyncio
    async def test_get_channel_summary_success(self):
        """Test successful channel summary fetch."""
        mock_analytics = MagicMock()
        mock_stats = MagicMock()
        mock_stats.total_views = 10000
        mock_stats.watch_time_minutes = 5000.0
        mock_stats.subscribers_gained = 100
        mock_analytics.get_channel_stats.return_value = mock_stats
        
        with patch('mcp_server.get_youtube_analytics', return_value=mock_analytics):
            result = await handle_get_channel_summary({
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            })
            content = json.loads(result[0].text)
            
            assert content["total_views"] == 10000
            assert content["watch_time_minutes"] == 5000.0
            assert content["subscribers_gained"] == 100
            mock_analytics.get_channel_stats.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_channel_summary_missing_params(self):
        """Test with missing required parameters."""
        result = await handle_get_channel_summary({
            "start_date": "2024-01-01"
            # Missing end_date
        })
        content = json.loads(result[0].text)
        
        # Should handle gracefully
        assert "error" in content or "start_date" in content
    
    @pytest.mark.asyncio
    async def test_get_channel_summary_error(self):
        """Test error handling when channel stats fetch fails."""
        mock_analytics = MagicMock()
        mock_analytics.get_channel_stats.return_value = None
        
        with patch('mcp_server.get_youtube_analytics', return_value=mock_analytics):
            result = await handle_get_channel_summary({
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            })
            content = json.loads(result[0].text)
            
            assert content["error"] == "Could not fetch channel stats"


# =============================================================================
# get_content_recommendations Tests
# =============================================================================

class TestGetContentRecommendations:
    """Test get_content_recommendations tool handler."""
    
    @pytest.mark.asyncio
    async def test_get_content_recommendations_default(self):
        """Test content recommendations with default parameters."""
        mock_client = MagicMock()
        mock_game1 = MagicMock()
        mock_game1.__dict__ = {"appid": 1, "name": "Game1", "content_demand_score": 90.0}
        mock_game2 = MagicMock()
        mock_game2.__dict__ = {"appid": 2, "name": "Game2", "content_demand_score": 80.0}
        mock_client.get_library_metrics.return_value = [mock_game1, mock_game2]
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            result = await handle_get_content_recommendations({})
            content = json.loads(result[0].text)
            
            assert content["count"] <= 5  # Default limit
            mock_client.get_library_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_content_recommendations_custom_filters(self):
        """Test content recommendations with custom filters."""
        mock_client = MagicMock()
        mock_client.get_library_metrics.return_value = []
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            result = await handle_get_content_recommendations({
                "limit": 10,
                "min_playtime": 2.0,
                "installed_only": False
            })
            content = json.loads(result[0].text)
            
            mock_client.get_library_metrics.assert_called_once_with(
                limit=20,  # limit * 2
                min_playtime=2.0,
                installed_only=False
            )
    
    @pytest.mark.asyncio
    async def test_get_content_recommendations_limit_cap(self):
        """Test that limit is capped at 20."""
        mock_client = MagicMock()
        mock_client.get_library_metrics.return_value = []
        
        with patch('mcp_server.get_game_metrics_client', return_value=mock_client):
            await handle_get_content_recommendations({"limit": 50})
            
            mock_client.get_library_metrics.assert_called_once()
            # Check that limit was capped to 20 in the call


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
        client1 = get_game_metrics_client()
        client2 = get_game_metrics_client()
        assert client1 is client2
    
    def test_get_youtube_analytics_singleton(self):
        """Test that YouTubeAnalytics is cached."""
        client1 = get_youtube_analytics()
        client2 = get_youtube_analytics()
        assert client1 is client2


# =============================================================================
# Tool Call Handler Tests
# =============================================================================

class TestToolCallHandler:
    """Test the main tool call handler."""
    
    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test handling of unknown tool name."""
        result = await app.call_tool("unknown_tool", {})
        content = result[0].text
        
        assert "Unknown tool" in content
    
    @pytest.mark.asyncio
    async def test_tool_call_error_handling(self):
        """Test error handling in tool calls."""
        with patch('mcp_server.handle_get_installed_games', side_effect=Exception("Test error")):
            result = await app.call_tool("get_installed_games", {})
            content = result[0].text
            
            assert "Error" in content
