# ADR-MCP-001: MCP Server for Claude Desktop Integration

## Status
Accepted

## Context
ContentPipeline functionality needs to be accessible from Claude Desktop for AI-assisted content creation workflows. Two integration approaches were considered:

1. **FastAPI HTTP Server**: REST API endpoints that Claude Desktop could call via HTTP
2. **MCP Server with stdio transport**: Model Context Protocol server using subprocess communication

FastAPI would require:
- Running a persistent web server process
- Managing CORS, authentication, and port conflicts
- Additional infrastructure for tower deployment
- More complex deployment story

MCP (Model Context Protocol) is the standard for Claude Desktop integrations, designed specifically for AI assistant tool exposure. It uses stdio transport (subprocess communication) which is simpler, more secure, and the recommended pattern for Claude Desktop.

## Decision
MCP Server with stdio transport. Create `mcp_server.py` exposing 5 ContentPipeline tools:
- `get_installed_games`: List installed Steam games
- `get_game_metrics`: Get enriched game metrics (Steam + SteamSpy + YouTube)
- `get_youtube_analytics`: Get video performance metrics
- `get_channel_summary`: Get channel performance summary
- `get_content_recommendations`: Get content recommendations based on metrics

Use the official `mcp` Python SDK. Configure Claude Desktop to run the server as a subprocess with Python interpreter at `C:\Python314\python.exe` and working directory at `C:\Github\GameReviewAgent\content-engine\`.

## Consequences
- Adds `mcp` dependency to requirements.txt
- Requires Claude Desktop configuration (documented in docs/mcp_setup.md)
- Simpler deployment: no web server, no ports, no CORS
- FastAPI deferred for future tower deployment if needed
- All ContentPipeline functionality accessible from Claude Desktop
- Lazy client initialization for efficient resource usage
