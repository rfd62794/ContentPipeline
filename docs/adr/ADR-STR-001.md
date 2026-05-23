# ADR-STR-001: Stream Launcher for YouTube Live

## Status
Accepted

## Context
The content pipeline currently supports automated Shorts production but lacks automated live streaming capabilities. To enable hands-off live streaming sessions, we need a system that can:

1. Launch OBS Studio with configured scenes
2. Launch games via Steam protocol URIs
3. Start YouTube Live streams via OBS websocket control
4. Manage stream metadata (title, description, tags, privacy)

Two approaches were considered:

1. **Manual workflow**: User manually starts OBS, launches game, and starts stream
   - Pros: Simple, no automation complexity
   - Cons: Defeats the purpose of automated content production, requires manual intervention

2. **Automated stream launcher**: Python script orchestrates OBS, Steam, and YouTube Live
   - Pros: Fully automated, consistent with existing pipeline automation, enables scheduled streams
   - Cons: Requires OBS websocket integration, external dependencies

The automated approach aligns with the project's goal of hands-off content production and enables future scheduling and batch processing capabilities.

## Decision
Implement an automated stream launcher with the following components:

1. **stream_launcher.py**: Pure and integration functions for stream orchestration
   - Pure functions: config loading, validation, URI building, title generation
   - Integration functions: OBS websocket connection, game launching, stream starting

2. **Stream YAML configs**: Game-specific stream configurations in `content-engine/streams/`
   - dorfromantik.yaml, stacklands.yaml, scritchy_scratchy.yaml
   - Fields: game, steam_appid, title, description, category, privacy, obs_scene, tags

3. **MCP tool integration**: Add `start_stream` tool to mcp_server.py
   - Enables Claude Desktop to trigger automated streams
   - Parameters: game_name (required), title (optional), privacy (optional)

4. **Dependencies**: Add obs-websocket-py for OBS websocket control
   - Python library for OBS Studio websocket API
   - Enables scene switching, stream control, and monitoring

5. **Environment configuration**: Add stream-specific secrets to .env
   - YOUTUBE_STREAM_KEY: YouTube stream key for RTMP
   - OBS_WEBSOCKET_PASSWORD: OBS websocket server password
   - OBS_EXE_PATH: Path to OBS Studio executable

## Consequences
- Adds obs-websocket-py dependency to requirements.txt
- Requires OBS Studio with websocket server enabled
- Requires YouTube stream key and OBS configuration
- Enables fully automated live streaming workflows
- Consistent with existing automated content production patterns
- Supports future features: scheduled streams, batch processing, stream monitoring
- Test coverage: 16 pure function tests (no integration tests for OBS/Steam/YouTube)
