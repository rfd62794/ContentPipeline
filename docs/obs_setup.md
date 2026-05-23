# OBS Studio Setup for Stream Launcher

This document describes the one-time OBS Studio configuration required for the stream launcher to work correctly.

## Prerequisites

- OBS Studio installed (version 28.0 or later)
- OBS WebSocket Server enabled (port 4455)
- Environment variables configured in `.env`:
  - `OBS_WEBSOCKET_PASSWORD` (optional, if password is set)
  - `OBS_EXE_PATH` (path to obs64.exe)

## Enable OBS WebSocket Server

1. Open OBS Studio
2. Go to **Tools** → **WebSocket Server Settings**
3. Enable the WebSocket Server:
   - Check "Enable WebSocket Server"
   - Port: `4455` (default)
   - Password: Set a password (optional but recommended)
4. If you set a password, add it to `.env`:
   ```
   OBS_WEBSOCKET_PASSWORD=your_password_here
   ```

## Create Scenes

Create the following scenes in OBS:

### 1. Starting Soon Scene
- **Scene Name:** `Starting Soon`
- **Sources:**
  - Browser Source: `file:///absolute/path/to/content-engine/overlays/starting_soon.html`
  - Width: 1920, Height: 1080
  - Background: Transparent (checked)

### 2. Gaming Scene
- **Scene Name:** `Gaming`
- **Sources:**
  - Game Capture (your game window)
  - Browser Source: `file:///absolute/path/to/content-engine/overlays/game_info.html`
    - Width: 400, Height: 160
    - Position: Bottom-left (X: 20, Y: 20)
    - Background: Transparent (checked)

### 3. BRB Scene
- **Scene Name:** `BRB`
- **Sources:**
  - Browser Source: `file:///absolute/path/to/content-engine/overlays/brb.html`
  - Width: 1920, Height: 1080
  - Background: Transparent (checked)

### 4. Ending Scene
- **Scene Name:** `Ending`
- **Sources:**
  - Browser Source: `file:///absolute/path/to/content-engine/overlays/ending.html`
  - Width: 1920, Height: 1080
  - Background: Transparent (checked)

## Configure Audio Sources

Ensure your microphone is configured in OBS:

1. Add **Audio Input Capture** source
2. Name it: `Mic/Aux` (or match your stream YAML `obs_mic_source` field)
3. Select your microphone device

## Configure Stream Settings

1. Go to **Settings** → **Stream**
2. Service: YouTube / YouTube Live
3. Stream Key: Add to `.env` as `YOUTUBE_STREAM_KEY`
4. Video Bitrate: 4500-6000 Kbps (adjust based on upload speed)
5. Audio Bitrate: 160 Kbps

## Update Stream YAML Files

Each game's stream YAML must reference the correct OBS scene names:

```yaml
game: Dorfromantik
steam_appid: 1146360
title: Building in Public - Dorfromantik
privacy: public
obs_scene: Gaming
obs_overlay_scene: BRB
obs_mic_source: Mic/Aux
game_process_name: Dorfromantik.exe
```

## Test Browser Sources

Before using the stream launcher, test each overlay:

1. Open each HTML file in a web browser using `file://` protocol
2. Verify:
   - Starting Soon: Progress bar animates, text displays correctly
   - BRB: Cursor blinks, text displays correctly
   - Game Info: Test with URL params: `game_info.html?game=Test&session=1&commits=5`
   - Ending: Test with URL params: `ending.html?commits=10`

## Troubleshooting

### Browser Source Not Loading
- Ensure the file path is absolute (not relative)
- Use forward slashes in file paths: `C:/Github/...` not `C:\Github\...`
- Check that the HTML file exists at the specified path

### WebSocket Connection Failed
- Verify OBS WebSocket Server is enabled
- Check port 4455 is not blocked by firewall
- Verify password matches `.env` if authentication is enabled

### Game Info Not Updating
- Ensure the StreamMonitor thread is running
- Check that `DEFAULT_REPO_PATH` is set correctly in `.env`
- Verify git is available in system PATH

### Scene Switching Not Working
- Verify scene names in YAML match OBS scene names exactly
- Check OBS WebSocket connection is established
- Test scene switching manually via OBS first

## File Path Reference

Replace `C:/Github/GameReviewAgent/content-engine/overlays/` with your actual absolute path in OBS browser sources.

**Windows Example:**
```
file:///C:/Github/GameReviewAgent/content-engine/overlays/starting_soon.html
```

**Linux/Mac Example:**
```
file:///home/user/GameReviewAgent/content-engine/overlays/starting_soon.html
```

## Next Steps

Once OBS is configured:
1. Test with `start_test_stream(game="Dorfromantik", test_mode="virtual_camera")`
2. Verify overlays display correctly in your webcam app
3. Test with `start_test_stream(game="Dorfromantik", test_mode="unlisted")`
4. Verify full stream workflow

This setup is a one-time configuration. Future streams will use the same scenes and sources.