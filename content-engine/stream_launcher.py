"""
Stream Launcher — CLI tool and MCP integration for YouTube live streaming.

Launches a designated game streaming on YouTube Live in under 60 seconds
from a single call. Integrates with OBS via WebSocket and YouTube via Data API.

Usage:
    python stream_launcher.py <game_name> [--title "..."] [--private]
    python stream_launcher.py dorfromantik
    python stream_launcher.py "Scritchy Scratchy" --title "First look"
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
import psutil

# Load .env from absolute path
load_dotenv(Path(__file__).parent / ".env")


def load_stream_config(yaml_path: Path) -> dict:
    """Load and return stream YAML config as dict."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def build_stream_title(config: dict) -> str:
    """Return title string from config. Max 100 chars (YouTube limit)."""
    title = config.get("title", "")
    if len(title) > 100:
        title = title[:100]
    return title


def build_youtube_stream_url(channel_handle: str) -> str:
    """Return full YouTube live URL for channel handle."""
    return f"https://www.youtube.com/{channel_handle}/live"


def get_steam_launch_uri(appid: int) -> str:
    """Return steam://rungameid/{appid} URI string."""
    return f"steam://rungameid/{appid}"


def validate_stream_config(config: dict) -> list[str]:
    """Return list of validation errors. Empty = valid.
    Check: game present, steam_appid is int, title <= 100 chars,
    privacy is public/unlisted/private, obs_scene present."""
    errors = []
    
    if not config.get("game"):
        errors.append("Missing required field: game")
    
    steam_appid = config.get("steam_appid")
    if steam_appid is None:
        errors.append("Missing required field: steam_appid")
    elif not isinstance(steam_appid, int):
        errors.append("steam_appid must be an integer")
    
    title = config.get("title", "")
    if len(title) > 100:
        errors.append("Title exceeds 100 character limit")
    
    privacy = config.get("privacy", "public")
    if privacy not in ["public", "unlisted", "private"]:
        errors.append(f"Invalid privacy value: {privacy}. Must be public, unlisted, or private")
    
    if not config.get("obs_scene"):
        errors.append("Missing required field: obs_scene")
    
    return errors


def find_stream_config(game_name: str, streams_dir: Path) -> Optional[Path]:
    """Case-insensitive search for stream YAML by game name.
    Returns Path if found, None if not found.
    Matches on filename stem or game field in YAML."""
    game_name_lower = game_name.lower()
    
    # First try exact filename match
    for yaml_file in streams_dir.glob("*.yaml"):
        if yaml_file.stem.lower() == game_name_lower:
            return yaml_file
    
    # Then try matching game field in YAML
    for yaml_file in streams_dir.glob("*.yaml"):
        try:
            config = load_stream_config(yaml_file)
            if config.get("game", "").lower() == game_name_lower:
                return yaml_file
        except Exception:
            continue
    
    return None


def ensure_obs_running(obs_exe_path: Optional[str] = None) -> bool:
    """
    Check if OBS is running. If not, launch it and wait up to 10 seconds
    for WebSocket to become available.
    obs_exe_path: override path to OBS64.exe. If None, checks common paths:
      C:/Program Files/obs-studio/bin/64bit/obs64.exe
    Returns True if OBS is ready, False if launch failed or timed out.
    """
    
    # Check if OBS is already running
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'obs' in proc.info['name'].lower():
            return True
    
    # Find OBS executable
    if obs_exe_path:
        exe_path = Path(obs_exe_path)
    else:
        common_paths = [
            "C:/Program Files/obs-studio/bin/64bit/obs64.exe",
            "C:/Program Files (x86)/obs-studio/bin/64bit/obs64.exe",
        ]
        for path in common_paths:
            if Path(path).exists():
                exe_path = Path(path)
                break
        else:
            print("Error: OBS executable not found in common paths")
            return False
    
    # Launch OBS
    print(f"Launching OBS from {exe_path}")
    try:
        subprocess.Popen([str(exe_path)], shell=True)
    except Exception as e:
        print(f"Error launching OBS: {e}")
        return False
    
    # Wait for OBS to start (up to 10 seconds)
    for i in range(10):
        time.sleep(1)
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'obs' in proc.info['name'].lower():
                print(f"OBS detected after {i+1} seconds")
                return True
    
    print("Error: OBS did not start within 10 seconds")
    return False


def launch_game(appid: int) -> None:
    """Launch game via Steam URI. subprocess.Popen, non-blocking."""
    uri = get_steam_launch_uri(appid)
    print(f"Launching game via Steam: {uri}")
    subprocess.Popen(["start", uri], shell=True)


def update_youtube_stream_title(title: str, description: str, 
                                 privacy: str, stream_key: str) -> bool:
    """Update YouTube live stream metadata via YouTube Data API v3.
    Uses existing OAuth from core.youtube_auth.
    Returns True on success, False on failure."""
    try:
        from core.youtube_auth import get_authenticated_service
        
        youtube = get_authenticated_service()
        
        # Get the live broadcast ID
        stream_key = os.getenv("YOUTUBE_STREAM_KEY")
        if not stream_key:
            print("Error: YOUTUBE_STREAM_KEY not found in environment")
            return False
        
        # List live broadcasts to find the one matching our stream key
        request = youtube.liveBroadcasts().list(
            part="id,snippet",
            mine=True
        )
        response = request.execute()
        
        broadcast_id = None
        for item in response.get("items", []):
            if item.get("snippet", {}).get("title") == stream_key:
                broadcast_id = item["id"]
                break
        
        if not broadcast_id:
            print("Error: Could not find live broadcast matching stream key")
            return False
        
        # Update the broadcast
        youtube.liveBroadcasts().update(
            part="snippet,status",
            body={
                "id": broadcast_id,
                "snippet": {
                    "title": title,
                    "description": description
                },
                "status": {
                    "privacyStatus": privacy
                }
            }
        ).execute()
        
        print(f"Updated YouTube stream title: {title}")
        return True
        
    except Exception as e:
        print(f"Error updating YouTube stream: {e}")
        return False


def connect_obs() -> object:
    """Connect to OBS via obs-websocket-py.
    Reads OBS_WEBSOCKET_PASSWORD from env.
    Default port 4455. Returns obs client object."""
    try:
        from obswebsocket import obsws
        
        password = os.getenv("OBS_WEBSOCKET_PASSWORD")
        if not password:
            print("Error: OBS_WEBSOCKET_PASSWORD not found in environment")
            return None
        
        obs = obsws(obsws_host="localhost", obsws_port=4455, password=password)
        obs.connect()
        print("Connected to OBS WebSocket")
        return obs
        
    except Exception as e:
        print(f"Error connecting to OBS: {e}")
        return None


def switch_obs_scene(obs_client: object, scene_name: str) -> None:
    """Switch OBS to named scene."""
    try:
        obs_client.call("SetCurrentScene", {"sceneName": scene_name})
        print(f"Switched OBS to scene: {scene_name}")
    except Exception as e:
        print(f"Error switching OBS scene: {e}")


def start_obs_stream(obs_client: object) -> None:
    """Start OBS streaming output."""
    try:
        obs_client.call("StartStopStreaming")
        print("Started OBS streaming")
    except Exception as e:
        print(f"Error starting OBS stream: {e}")


def start_stream(game_name: str, 
                 title: Optional[str] = None,
                 privacy: str = "public",
                 obs_scene: Optional[str] = None) -> dict:
    """
    Full stream launch sequence:
    1. Find stream config for game_name
    2. Validate config
    3. Update YouTube stream title/description
    4. Launch game via Steam
    5. Connect to OBS
    6. Switch to correct scene
    7. Start OBS streaming
    8. Return status dict with stream URL
    
    title, privacy, obs_scene override YAML values if provided.
    """
    streams_dir = Path(__file__).parent / "streams"
    
    # 1. Find stream config
    config_path = find_stream_config(game_name, streams_dir)
    if not config_path:
        return {
            "success": False,
            "error": f"Stream config not found for game: {game_name}"
        }
    
    # 2. Load and validate config
    config = load_stream_config(config_path)
    errors = validate_stream_config(config)
    if errors:
        return {
            "success": False,
            "error": f"Config validation failed: {', '.join(errors)}"
        }
    
    # Override with provided parameters
    final_title = title if title else config.get("title")
    final_privacy = privacy if privacy else config.get("privacy", "public")
    final_scene = obs_scene if obs_scene else config.get("obs_scene")
    
    # 3. Update YouTube stream metadata
    stream_key = os.getenv("YOUTUBE_STREAM_KEY")
    if not stream_key:
        return {
            "success": False,
            "error": "YOUTUBE_STREAM_KEY not found in environment"
        }
    
    print(f"Updating YouTube stream: {final_title}")
    if not update_youtube_stream_title(final_title, config.get("description", ""), final_privacy, stream_key):
        return {
            "success": False,
            "error": "Failed to update YouTube stream metadata"
        }
    
    # 4. Launch game (non-blocking)
    print(f"Launching game: {config.get('game')}")
    launch_game(config.get("steam_appid"))
    
    # 5. Ensure OBS is running
    obs_exe_path = os.getenv("OBS_EXE_PATH")
    if not ensure_obs_running(obs_exe_path):
        return {
            "success": False,
            "error": "Failed to ensure OBS is running"
        }
    
    # 6. Connect to OBS
    obs_client = connect_obs()
    if not obs_client:
        return {
            "success": False,
            "error": "Failed to connect to OBS"
        }
    
    # 7. Switch OBS scene
    print(f"Switching OBS scene to: {final_scene}")
    switch_obs_scene(obs_client, final_scene)
    
    # 8. Start OBS streaming
    print("Starting OBS streaming")
    start_obs_stream(obs_client)
    
    # 9. Return success with stream URL
    channel_handle = "@robertfloyddugger4516"
    stream_url = build_youtube_stream_url(channel_handle)
    
    return {
        "success": True,
        "stream_url": stream_url,
        "game": config.get("game"),
        "title": final_title
    }


def main() -> None:
    """
    CLI: python stream_launcher.py <game_name> [--title "..."] [--private]
    
    Examples:
      python stream_launcher.py dorfromantik
      python stream_launcher.py "Scritchy Scratchy" --title "First look"
    
    Prints: "Live at youtube.com/@robertfloyddugger4516"
    """
    if len(sys.argv) < 2:
        print("Usage: python stream_launcher.py <game_name> [--title \"...\"] [--private]")
        print("Example: python stream_launcher.py dorfromantik")
        sys.exit(1)
    
    game_name = sys.argv[1]
    title = None
    privacy = "public"
    
    # Parse optional arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--title" and i + 1 < len(sys.argv):
            title = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--private":
            privacy = "private"
            i += 1
        else:
            print(f"Unknown argument: {sys.argv[i]}")
            sys.exit(1)
    
    result = start_stream(game_name, title=title, privacy=privacy)
    
    if result["success"]:
        print(f"Live at {result['stream_url']}")
    else:
        print(f"Error: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
