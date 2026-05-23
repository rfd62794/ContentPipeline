# MCP Server Setup for Claude Desktop

This guide explains how to configure Claude Desktop to use the ContentPipeline MCP server.

## Prerequisites

1. **Python 3.14** installed at `C:\Python314\python.exe`
2. **ContentPipeline repository** cloned to `C:\Github\GameReviewAgent\`
3. **Dependencies installed** in the content-engine directory:
   ```bash
   cd C:\Github\GameReviewAgent\content-engine
   pip install -r requirements.txt
   ```

## Claude Desktop Configuration

### Windows Configuration File Location

Claude Desktop stores its configuration in:
```
C:\Users\<username>\AppData\Roaming\Claude\claude_desktop_config.json
```

### Configuration Snippet

Add the following to your `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "content-pipeline": {
            "command": "C:\\Python314\\python.exe",
            "args": ["C:\\Github\\GameReviewAgent\\content-engine\\mcp_server.py"],
            "cwd": "C:\\Github\\GameReviewAgent\\content-engine"
        }
    }
}
```

### Full Example Configuration

If you have other MCP servers configured, your file might look like this:

```json
{
    "mcpServers": {
        "content-pipeline": {
            "command": "C:\\Python314\\python.exe",
            "args": ["C:\\Github\\GameReviewAgent\\content-engine\\mcp_server.py"],
            "cwd": "C:\\Github\\GameReviewAgent\\content-engine"
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\Users\\<username>\\Documents"]
        }
    }
}
```

## Environment Variables

The MCP server requires the following environment variables to be set in the content-engine directory:

### Steam API (for game metrics)
- `STEAM_API_KEY`: Your Steam Web API key
- `STEAM_ID`: Your Steam user ID

### YouTube API (for analytics)
- `YOUTUBE_CLIENT_ID`: YouTube OAuth client ID
- `YOUTUBE_CLIENT_SECRET`: YouTube OAuth client secret

Create a `.env` file in `C:\Github\GameReviewAgent\content-engine\`:

```env
STEAM_API_KEY=your_steam_api_key_here
STEAM_ID=your_steam_id_here
YOUTUBE_CLIENT_ID=your_youtube_client_id_here
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret_here
```

## Available Tools

Once configured, Claude Desktop will have access to the following tools:

### 1. get_installed_games
List all installed Steam games from local ACF files.

**Parameters:**
- `steam_path` (optional): Path to Steam installation directory (default: C:/Program Files (x86)/Steam)

**Example:**
```
Get my installed Steam games
```

### 2. get_game_metrics
Get enriched game metrics combining Steam, SteamSpy, and YouTube data.

**Parameters:**
- `appid` (optional): Steam AppID of the game
- `limit` (optional): Number of games to return (default: 10, max: 50)
- `min_playtime` (optional): Minimum playtime in hours (default: 0)
- `installed_only` (optional): Only return installed games (default: false)

**Example:**
```
Get game metrics for my top 10 installed games with at least 5 hours of playtime
```

### 3. get_youtube_analytics
Get video performance metrics from YouTube Analytics API.

**Parameters:**
- `video_id` (required): YouTube video ID
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

**Example:**
```
Get YouTube analytics for video abc123 from 2024-01-01 to 2024-01-31
```

### 4. get_channel_summary
Get channel performance summary from YouTube Analytics API.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

**Example:**
```
Get my channel summary for January 2024
```

### 5. get_content_recommendations
Get content recommendations based on game metrics and YouTube performance.

**Parameters:**
- `limit` (optional): Number of recommendations to return (default: 5, max: 20)
- `min_playtime` (optional): Minimum playtime in hours (default: 1.0)
- `installed_only` (optional): Only recommend installed games (default: true)

**Example:**
```
Get content recommendations for my installed games with at least 2 hours of playtime
```

## Testing the Configuration

1. **Restart Claude Desktop** after updating the configuration file
2. **Check the MCP server status** in Claude Desktop settings
3. **Try a simple command** like "Get my installed Steam games"
4. **Check the logs** if you encounter errors (Claude Desktop logs MCP server output)

## Troubleshooting

### MCP Server Not Starting
- Verify Python path is correct: `C:\Python314\python.exe`
- Verify repository path is correct: `C:\Github\GameReviewAgent\content-engine`
- Check that all dependencies are installed: `pip install -r requirements.txt`

### Tools Not Available
- Restart Claude Desktop after configuration changes
- Check that `.env` file exists with required API keys
- Verify the MCP server is running (check Claude Desktop logs)

### API Errors
- Verify Steam API key and Steam ID are correct
- Verify YouTube OAuth credentials are correct
- Check that OAuth token file `.youtube_token.json` exists (created on first use)

### Permission Errors
- Ensure Claude Desktop has permission to access the repository directory
- Check that `.env` file is not gitignored (it should be, but Claude Desktop needs to read it)

## Architecture Decision

For details on why MCP was chosen over FastAPI, see [ADR-MCP-001.md](../adr/ADR-MCP-001.md).

## Next Steps

After successful configuration:
1. Test each tool individually
2. Try complex queries combining multiple tools
3. Use the tools for content planning and game selection
4. Integrate with your content creation workflow
