"""
MCP Server for ContentPipeline Tools

Exposes ContentPipeline functionality to Claude Desktop via MCP (Model Context Protocol).
Uses stdio transport for subprocess communication.

Tools:
- get_installed_games: List installed Steam games
- get_game_metrics: Get enriched game metrics (Steam + SteamSpy + YouTube)
- get_youtube_analytics: Get video performance metrics
- get_channel_summary: Get channel performance summary
- get_content_recommendations: Get content recommendations based on metrics

Usage:
    python mcp_server.py

Claude Desktop Configuration:
    Add to Claude Desktop config.json:
    {
        "mcpServers": {
            "content-pipeline": {
                "command": "C:\\Python314\\python.exe",
                "args": ["C:\\Github\\GameReviewAgent\\content-engine\\mcp_server.py"],
                "cwd": "C:\\Github\\GameReviewAgent\\content-engine"
            }
        }
    }
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ContentPipeline imports
# Export for tests
__all__ = ["steam_get_installed_games"]
from steam_library import get_installed_games as steam_get_installed_games, SteamLibrary, GameInfo
from game_metrics import GameMetricsClient, GameMetrics
from youtube_analytics import YouTubeAnalytics, VideoStats, ChannelStats

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
app = Server("content-pipeline")

# Global clients (initialized lazily)
_steam_library: Optional[SteamLibrary] = None
_game_metrics_client: Optional[GameMetricsClient] = None
_youtube_analytics: Optional[YouTubeAnalytics] = None


def get_steam_library() -> SteamLibrary:
    """Get or create SteamLibrary client."""
    global _steam_library
    if _steam_library is None:
        _steam_library = SteamLibrary()
    return _steam_library


def get_game_metrics_client() -> GameMetricsClient:
    """Get or create GameMetricsClient."""
    global _game_metrics_client
    if _game_metrics_client is None:
        _game_metrics_client = GameMetricsClient()
    return _game_metrics_client


def get_youtube_analytics() -> YouTubeAnalytics:
    """Get or create YouTubeAnalytics client."""
    global _youtube_analytics
    if _youtube_analytics is None:
        _youtube_analytics = YouTubeAnalytics()
    return _youtube_analytics


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_installed_games",
            description="List all installed Steam games from local ACF files",
            inputSchema={
                "type": "object",
                "properties": {
                    "steam_path": {
                        "type": "string",
                        "description": "Path to Steam installation directory (default: C:/Program Files (x86)/Steam)"
                    }
                }
            }
        ),
        Tool(
            name="get_game_metrics",
            description="Get enriched game metrics combining Steam, SteamSpy, and YouTube data",
            inputSchema={
                "type": "object",
                "properties": {
                    "appid": {
                        "type": "integer",
                        "description": "Steam AppID of the game"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of games to return (default: 10, max: 50)"
                    },
                    "min_playtime": {
                        "type": "number",
                        "description": "Minimum playtime in hours (default: 0)"
                    },
                    "installed_only": {
                        "type": "boolean",
                        "description": "Only return installed games (default: false)"
                    }
                }
            }
        ),
        Tool(
            name="get_youtube_analytics",
            description="Get video performance metrics from YouTube Analytics API",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    }
                },
                "required": ["video_id", "start_date", "end_date"]
            }
        ),
        Tool(
            name="get_channel_summary",
            description="Get channel performance summary from YouTube Analytics API",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        ),
        Tool(
            name="get_content_recommendations",
            description="Get content recommendations based on game metrics and YouTube performance",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recommendations to return (default: 5, max: 20)"
                    },
                    "min_playtime": {
                        "type": "number",
                        "description": "Minimum playtime in hours (default: 1.0)"
                    },
                    "installed_only": {
                        "type": "boolean",
                        "description": "Only recommend installed games (default: true)"
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_installed_games":
            return await handle_get_installed_games(arguments)
        elif name == "get_game_metrics":
            return await handle_get_game_metrics(arguments)
        elif name == "get_youtube_analytics":
            return await handle_get_youtube_analytics(arguments)
        elif name == "get_channel_summary":
            return await handle_get_channel_summary(arguments)
        elif name == "get_content_recommendations":
            return await handle_get_content_recommendations(arguments)
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def handle_get_installed_games(arguments: Any) -> list[TextContent]:
    """Handle get_installed_games tool call."""
    steam_path = arguments.get("steam_path")
    if steam_path:
        games = steam_get_installed_games(Path(steam_path))
    else:
        games = steam_get_installed_games()
    
    result = {
        "count": len(games),
        "games": games
    }
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def handle_get_game_metrics(arguments: Any) -> list[TextContent]:
    """Handle get_game_metrics tool call."""
    appid = arguments.get("appid")
    limit = arguments.get("limit", 10)
    min_playtime = arguments.get("min_playtime", 0)
    installed_only = arguments.get("installed_only", False)
    
    client = get_game_metrics_client()
    
    if appid:
        # Get metrics for specific game
        metrics = client.get_game_metrics(appid)
        result = {
            "count": 1,
            "games": [metrics.__dict__ if metrics else None]
        }
    else:
        # Get metrics for multiple games
        limit = min(limit, 50)  # Cap at 50
        games = client.get_library_metrics(
            limit=limit,
            min_playtime=min_playtime,
            installed_only=installed_only
        )
        result = {
            "count": len(games),
            "games": [g.__dict__ if hasattr(g, '__dict__') else g for g in games]
        }
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def handle_get_youtube_analytics(arguments: Any) -> list[TextContent]:
    """Handle get_youtube_analytics tool call."""
    video_id = arguments.get("video_id")
    start_date = arguments.get("start_date")
    end_date = arguments.get("end_date")
    
    analytics = get_youtube_analytics()
    stats = analytics.get_video_stats(video_id, start_date, end_date)
    
    if stats:
        result = {
            "video_id": video_id,
            "views": stats.views,
            "watch_time_minutes": stats.watch_time_minutes,
            "avg_view_duration_seconds": stats.avg_view_duration_seconds,
            "avg_view_percentage": stats.avg_view_percentage,
            "subscribers_gained": stats.subscribers_gained,
            "likes": stats.likes,
            "start_date": start_date,
            "end_date": end_date
        }
    else:
        result = {
            "error": "Could not fetch video stats",
            "video_id": video_id
        }
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def handle_get_channel_summary(arguments: Any) -> list[TextContent]:
    """Handle get_channel_summary tool call."""
    start_date = arguments.get("start_date")
    end_date = arguments.get("end_date")
    
    analytics = get_youtube_analytics()
    stats = analytics.get_channel_stats(start_date, end_date)
    
    if stats:
        result = {
            "total_views": stats.total_views,
            "watch_time_minutes": stats.watch_time_minutes,
            "subscribers_gained": stats.subscribers_gained,
            "start_date": start_date,
            "end_date": end_date
        }
    else:
        result = {
            "error": "Could not fetch channel stats",
            "start_date": start_date,
            "end_date": end_date
        }
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def handle_get_content_recommendations(arguments: Any) -> list[TextContent]:
    """Handle get_content_recommendations tool call."""
    limit = arguments.get("limit", 5)
    min_playtime = arguments.get("min_playtime", 1.0)
    installed_only = arguments.get("installed_only", True)
    
    limit = min(limit, 20)  # Cap at 20
    
    client = get_game_metrics_client()
    
    # Get library metrics with filters
    games = client.get_library_metrics(
        limit=limit * 2,  # Get more to filter
        min_playtime=min_playtime,
        installed_only=installed_only
    )
    
    # Sort by content demand score (descending)
    from game_metrics import sort_by_metric
    sorted_games = sort_by_metric(
        [g.__dict__ if hasattr(g, '__dict__') else g for g in games],
        'content_demand_score',
        descending=True
    )
    
    # Return top recommendations
    recommendations = sorted_games[:limit]
    
    result = {
        "count": len(recommendations),
        "recommendations": recommendations
    }
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def main():
    """Main entry point for MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
