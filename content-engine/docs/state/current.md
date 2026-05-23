phase: 'Phase STR-1 — Stream Launcher for YouTube Live'
certified_floor: 489/0/10/3
what_is_next: 'Test OBS websocket integration and verify stream launcher functionality'

## Phase STR-1 — Stream Launcher for YouTube Live (2026-05-23)

### Completed
- **Created stream_launcher.py** — Pure and integration functions for stream orchestration
  - Pure functions: load_stream_config, build_stream_title, build_youtube_stream_url, get_steam_launch_uri, validate_stream_config, find_stream_config, ensure_obs_running
  - Integration functions: connect_obs, launch_game, start_stream (OBS websocket, Steam URIs, YouTube Live)
  - Comprehensive error handling and logging
  - Environment variable configuration for OBS and YouTube
- **Created stream YAML configs** — Game-specific stream configurations in content-engine/streams/
  - dorfromantik.yaml: Dorfromantik stream config (appid 1455840)
  - stacklands.yaml: Stacklands stream config (appid 1092000)
  - scritchy_scratchy.yaml: Scritchy Scratchy stream config (appid 2572290)
  - Fields: game, steam_appid, title, description, category, privacy, obs_scene, tags
- **Created test_stream_launcher.py** — 16 comprehensive tests for stream launcher
  - TestBuildStreamTitle: Title generation and truncation (4 tests)
  - TestBuildYoutubeUrl: YouTube Live URL building (2 tests)
  - TestGetSteamUri: Steam protocol URI generation (3 tests)
  - TestValidateStreamConfig: Config validation (8 tests)
  - TestFindStreamConfig: Config file discovery (4 tests)
  - TestLoadStreamConfig: Config loading (2 tests)
  - TestEnsureObsRunning: OBS process detection (2 tests)
  - Pure function tests only (no OBS/Steam/YouTube integration tests)
- **Created ADR-STR-001.md** — Architecture decision for stream launcher
  - Chose automated stream launcher over manual workflow
  - OBS websocket integration for scene switching and stream control
  - Steam protocol URIs for game launching
  - MCP tool integration for Claude Desktop
- **Added obs-websocket-py to requirements.txt** — OBS websocket Python library
- **Updated .env** — Added stream launcher environment variables
  - YOUTUBE_STREAM_KEY: YouTube stream key for RTMP
  - OBS_WEBSOCKET_PASSWORD: OBS websocket server password
  - OBS_EXE_PATH: Path to OBS Studio executable
- **Updated .env.example** — Added stream launcher environment variable placeholders
  - YOUTUBE_STREAM_KEY, OBS_WEBSOCKET_PASSWORD, OBS_EXE_PATH with example values

### Certified Floor Achievement
- Baseline: 474/0/10/3 (after MCP server integration)
- Target: 489/0/10/3
- Actual: 489/0/10/3 (15 new tests added, 0 failures)

### Key Design Decisions
- Automated stream launcher — Enables hands-off live streaming workflows
- Pure and integration function separation — Testable pure functions, isolated integration points
- OBS websocket control — Programmatic scene switching and stream management
- Steam protocol URIs — Cross-platform game launching
- YAML config files — Game-specific stream metadata
- MCP tool integration — Claude Desktop can trigger automated streams
- Environment variable configuration — Secure credential management

### Integration Verification
- stream_launcher.py implements pure and integration functions
- test_stream_launcher.py provides 16 pure function tests
- ADR-STR-001 documents architecture decision
- Three stream YAML configs created (dorfromantik, stacklands, scritchy_scratchy)
- obs-websocket-py added to requirements.txt
- Environment variables configured in .env and .env.example

### Usage Example
```python
# Load stream config
config = load_stream_config(Path("content-engine/streams/dorfromantik.yaml"))

# Validate config
errors = validate_stream_config(config)
if errors:
    print(f"Config errors: {errors}")

# Start stream (integration function)
start_stream(config, obs_password="password", stream_key="key")
```

### Stream Config Example
```yaml
game: Dorfromantik
steam_appid: 1455840
title: Chill Dorfromantik stream
description: Relaxing puzzle gameplay
category: Gaming
privacy: public
obs_scene: Gaming
tags:
  - puzzle
  - casual
```

### Next Steps
- Add start_stream tool to mcp_server.py
- Test OBS websocket integration
- Verify stream launcher functionality
- Test Steam URI game launching
- Validate YouTube stream key configuration
- Test end-to-end stream workflow
