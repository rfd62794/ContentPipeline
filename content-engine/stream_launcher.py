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
import time
import threading
import signal
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
import psutil

try:
    import win32gui
except ImportError:
    win32gui = None

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
    privacy is public/unlisted/private, obs_scene present,
    obs_overlay_scene present, obs_mic_source present.
    game_process_name is optional (will be auto-detected if missing).
    test_mode is optional (unlisted, youtube_test, virtual_camera)."""
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
    
    if not config.get("obs_overlay_scene"):
        errors.append("Missing required field: obs_overlay_scene")
    
    if not config.get("obs_mic_source"):
        errors.append("Missing required field: obs_mic_source")
    
    # game_process_name is optional - will be auto-detected if missing
    
    # test_mode is optional - validate if present
    test_mode = config.get("test_mode")
    if test_mode and test_mode not in ["unlisted", "youtube_test", "virtual_camera"]:
        errors.append(f"Invalid test_mode value: {test_mode}. Must be unlisted, youtube_test, or virtual_camera")
    
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


def get_active_window_title() -> str:
    """Get the title of the currently active window.
    Returns empty string if unable to detect."""
    try:
        if win32gui:
            return win32gui.GetWindowText(win32gui.GetForegroundWindow())
        else:
            return ""
    except Exception:
        return ""


def is_game_focused(window_title: str, game_name: str) -> bool:
    """Check if the active window is the game window.
    Case-insensitive partial match on game name in window title."""
    if not window_title:
        return False
    return game_name.lower() in window_title.lower()


def is_game_running(process_name: str) -> bool:
    """Check if a game process is currently running.
    Case-insensitive exact match on process name."""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
            return True
    return False


def load_game_registry() -> dict:
    """Load registry JSON. Return empty dict if file missing."""
    registry_path = Path(__file__).parent / "game_registry.json"
    try:
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading game registry: {e}")
        return {}


def save_game_registry(registry: dict) -> None:
    """Save registry to JSON. Atomic write."""
    registry_path = Path(__file__).parent / "game_registry.json"
    try:
        # Write to temp file first, then rename for atomic write
        temp_path = registry_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(registry, f, indent=2)
        temp_path.replace(registry_path)
    except Exception as e:
        print(f"Error saving game registry: {e}")


def update_game_registry_entry(registry: dict, appid: int, exe_name: str, install_path: str, session_count: int = 0) -> dict:
    """Return new registry dict with updated entry.
    Sets last_seen to current ISO datetime.
    Does not mutate input dict."""
    # Create a copy to avoid mutation
    new_registry = registry.copy()
    new_registry[str(appid)] = {
        "exe_name": exe_name,
        "install_path": str(install_path),
        "last_seen": datetime.now().isoformat(),
        "session_count": session_count
    }
    return new_registry


def get_exe_from_registry(registry: dict, appid: int) -> Optional[str]:
    """Return exe_name from registry if appid exists.
    Return None if not found."""
    entry = registry.get(str(appid))
    if entry:
        return entry.get("exe_name")
    return None


def find_active_repo(search_path: str) -> Optional[str]:
    """
    Scan search_path for directories containing .git/.
    Return path of repo with most recent commit timestamp.
    Returns None if no git repos found.
    search_path default: C:/Github/
    """
    try:
        search_dir = Path(search_path)
        if not search_dir.exists():
            return None
        
        repos_with_timestamps = []
        
        # Scan for .git directories
        for git_dir in search_dir.rglob(".git"):
            repo_path = git_dir.parent
            try:
                # Get most recent commit timestamp
                result = subprocess.run(
                    ["git", "-C", str(repo_path), "log", "-1", "--format=%ct"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    timestamp = int(result.stdout.strip())
                    repos_with_timestamps.append((repo_path, timestamp))
            except Exception:
                continue
        
        if not repos_with_timestamps:
            return None
        
        # Return repo with most recent commit
        most_recent = max(repos_with_timestamps, key=lambda x: x[1])
        return str(most_recent[0])
        
    except Exception:
        return None


def count_commits_since(repo_path: str, since_dt: datetime) -> int:
    """
    Run: git -C repo_path log --oneline --since="{since_dt.isoformat()}"
    Count lines in output.
    Returns 0 on any error (git not found, not a repo, etc.).
    """
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "--oneline", f"--since={since_dt.isoformat()}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            return len([line for line in lines if line.strip()])
        return 0
    except Exception:
        return 0


def build_game_info_url(
    overlay_path: str,
    game_name: str,
    session_number: int,
    commit_count: int
) -> str:
    """
    Build file:// URL with query params for game_info.html.
    Returns properly encoded URL string.
    """
    from urllib.parse import quote
    
    # Convert to absolute path if not already
    overlay_abs = Path(overlay_path).absolute()
    
    # Build URL with query parameters
    url = f"file:///{overlay_abs.as_posix()}?game={quote(game_name)}&session={session_number}&commits={commit_count}"
    return url


def find_game_exe(steam_appid: int, steam_path: Optional[Path] = None) -> Optional[str]:
    """Find the game executable using registry first, then fallback to scanning.
    Looks up installdir from steam_library ACF parser, then scans
    C:/Program Files (x86)/Steam/steamapps/common/{installdir}/
    Returns filename of largest .exe found, or None if not found."""
    try:
        # 1. Load registry
        registry = load_game_registry()
        
        # 2. Check registry for appid
        registry_exe = get_exe_from_registry(registry, steam_appid)
        if registry_exe:
            # 3. Verify exe exists at install_path
            entry = registry.get(str(steam_appid))
            install_path = Path(entry.get("install_path", "")) if entry else None
            if install_path and install_path.exists():
                exe_full_path = install_path / registry_exe
                if exe_full_path.exists():
                    # Update last_seen and save
                    updated_registry = update_game_registry_entry(
                        registry, steam_appid, registry_exe, install_path
                    )
                    save_game_registry(updated_registry)
                    print(f"Using cached exe from registry: {registry_exe}")
                    return registry_exe
                else:
                    print(f"Cached exe not found at {exe_full_path}, falling through to scan")
            else:
                print(f"Cached install path not found, falling through to scan")
        
        # 4. Fall through to full scan
        from steam_library import SteamLibrary
        
        # Initialize Steam library
        if steam_path is None:
            steam_path = Path("C:/Program Files (x86)/Steam")
        
        steam_lib = SteamLibrary(steam_path)
        
        # Get game info to find installdir
        games = steam_lib.get_installed_games()
        game_info = None
        for game in games:
            if game.appid == steam_appid:
                game_info = game
                break
        
        if not game_info or not game_info.installdir:
            print(f"Could not find installdir for appid {steam_appid}")
            return None
        
        # Scan the install directory for .exe files
        install_dir = steam_path / "steamapps" / "common" / game_info.installdir
        if not install_dir.exists():
            print(f"Install directory not found: {install_dir}")
            return None
        
        # Find all .exe files and their sizes
        exe_files = []
        for exe_path in install_dir.rglob("*.exe"):
            try:
                size = exe_path.stat().st_size
                exe_files.append((exe_path.name, size))
            except Exception:
                continue
        
        if not exe_files:
            print(f"No .exe files found in {install_dir}")
            return None
        
        # 5. Return the largest .exe file and update registry
        largest_exe = max(exe_files, key=lambda x: x[1])
        exe_name = largest_exe[0]
        print(f"Found game executable: {exe_name} ({largest_exe[1] / (1024*1024):.1f} MB)")
        
        # Update registry with scan result
        updated_registry = update_game_registry_entry(registry, steam_appid, exe_name, install_dir)
        save_game_registry(updated_registry)
        
        return exe_name
        
    except Exception as e:
        print(f"Error finding game executable: {e}")
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
    Reads OBS_WEBSOCKET_PASSWORD from env (optional).
    Default port 4455. Returns obs client object."""
    try:
        from obswebsocket import obsws
        
        password = os.getenv("OBS_WEBSOCKET_PASSWORD", "")
        
        if password:
            # Connect with authentication
            obs = obsws(host="localhost", port=4455, password=password)
            print("Connecting to OBS WebSocket with authentication")
        else:
            # Connect without authentication
            obs = obsws(host="localhost", port=4455, password="")
            print("Connecting to OBS WebSocket without authentication")
        
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


def stop_obs_stream(obs_client: object) -> None:
    """Stop OBS streaming output."""
    try:
        obs_client.call("StartStopStreaming")
        print("Stopped OBS streaming")
    except Exception as e:
        print(f"Error stopping OBS stream: {e}")


def mute_obs_mic(obs_client: object, mic_source: str) -> None:
    """Mute OBS microphone source."""
    try:
        obs_client.call("SetMute", {"source": mic_source, "mute": True})
        print(f"Muted OBS mic: {mic_source}")
    except Exception as e:
        print(f"Error muting OBS mic: {e}")


def unmute_obs_mic(obs_client: object, mic_source: str) -> None:
    """Unmute OBS microphone source."""
    try:
        obs_client.call("SetMute", {"source": mic_source, "mute": False})
        print(f"Unmuted OBS mic: {mic_source}")
    except Exception as e:
        print(f"Error unmuting OBS mic: {e}")


class StreamMonitor:
    """Background thread for monitoring game focus and process status.
    Handles focus loss → overlay + mic mute, game close → end stream.
    Also updates commit counter every 60 seconds."""
    
    def __init__(self, obs_client: object, config: dict, stream_start_time: datetime, session_count: int):
        self.obs_client = obs_client
        self.config = config
        self.running = True
        self.game_name = config.get("game")
        self.game_process_name = config.get("game_process_name")
        self.obs_game_scene = config.get("obs_scene")
        self.obs_overlay_scene = config.get("obs_overlay_scene")
        self.obs_mic_source = config.get("obs_mic_source")
        self.was_focused = True
        self.stream_start_time = stream_start_time
        self.session_count = session_count
        self.last_commit_update = time.time()
        self.repo_path = os.getenv("DEFAULT_REPO_PATH", "C:/Github/")
        
    def run(self):
        """Main monitoring loop. Runs in daemon thread."""
        print(f"Stream monitor started for {self.game_name}")
        
        while self.running:
            try:
                # Check if game is still running
                if not is_game_running(self.game_process_name):
                    print(f"Game closed — stream ended")
                    stop_obs_stream(self.obs_client)
                    self.running = False
                    break
                
                # Check window focus
                window_title = get_active_window_title()
                is_focused = is_game_focused(window_title, self.game_name)
                
                # Focus lost → switch to overlay + mute mic
                if self.was_focused and not is_focused:
                    print(f"Focus lost — switching to overlay scene")
                    switch_obs_scene(self.obs_client, self.obs_overlay_scene)
                    mute_obs_mic(self.obs_client, self.obs_mic_source)
                    self.was_focused = False
                
                # Focus returned → switch back to game + unmute mic
                elif not self.was_focused and is_focused:
                    print(f"Focus returned — switching to game scene")
                    switch_obs_scene(self.obs_client, self.obs_game_scene)
                    unmute_obs_mic(self.obs_client, self.obs_mic_source)
                    self.was_focused = True
                
                # Update commit counter every 60 seconds
                current_time = time.time()
                if current_time - self.last_commit_update >= 60:
                    self.update_commit_counter()
                    self.last_commit_update = current_time
                
                # Sleep for 2 seconds before next check
                time.sleep(2)
                
            except Exception as e:
                print(f"Stream monitor error: {e}")
                time.sleep(2)
        
        print("Stream monitor stopped")
    
    def update_commit_counter(self):
        """Update the game_info overlay with current commit count."""
        try:
            # Find active repo
            active_repo = find_active_repo(self.repo_path)
            if not active_repo:
                print("No active git repo found for commit counter")
                return
            
            # Count commits since stream start
            commit_count = count_commits_since(active_repo, self.stream_start_time)
            print(f"Commits since stream start: {commit_count}")
            
            # Build new game_info URL
            overlay_path = Path(__file__).parent / "overlays" / "game_info.html"
            new_url = build_game_info_url(
                str(overlay_path),
                self.game_name,
                self.session_count,
                commit_count
            )
            
            # Update OBS browser source (would need OBS websocket call to refresh URL)
            # This is a placeholder - actual implementation depends on OBS source naming
            print(f"Would update game_info overlay to: {new_url}")
            
        except Exception as e:
            print(f"Error updating commit counter: {e}")
    
    def stop(self):
        """Stop the monitor thread."""
        self.running = False


def start_stream(game_name: str, 
                 title: Optional[str] = None,
                 privacy: str = "public",
                 obs_scene: Optional[str] = None,
                 enable_monitor: bool = True) -> dict:
    """
    Full stream launch sequence:
    1. Find stream config for game_name
    2. Validate config
    3. Update YouTube stream title/description
    4. Launch game via Steam
    5. Connect to OBS
    6. Switch to correct scene
    7. Start OBS streaming
    8. Start stream monitor (if enabled)
    9. Return status dict with stream URL
    
    title, privacy, obs_scene override YAML values if provided.
    enable_monitor controls whether to start the background monitoring thread.
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
    
    # Auto-detect game_process_name if not in YAML
    if not config.get("game_process_name"):
        steam_appid = config.get("steam_appid")
        print(f"Auto-detecting game executable for appid {steam_appid}")
        detected_exe = find_game_exe(steam_appid)
        if detected_exe:
            config["game_process_name"] = detected_exe
            print(f"Auto-detected game_process_name: {detected_exe}")
        else:
            print("Warning: Could not auto-detect game_process_name. Process monitoring will be disabled.")
            enable_monitor = False
    
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
    
    # 9. Track session count in registry
    steam_appid = config.get("steam_appid")
    registry = load_game_registry()
    entry = registry.get(str(steam_appid), {})
    session_count = entry.get("session_count", 0) + 1
    registry = update_game_registry_entry(
        registry, steam_appid,
        exe_name=entry.get("exe_name"),
        install_path=entry.get("install_path"),
        session_count=session_count
    )
    save_game_registry(registry)
    print(f"Session count for {config.get('game')}: {session_count}")
    
    # 10. Start stream monitor (if enabled)
    monitor_thread = None
    if enable_monitor:
        stream_start_time = datetime.now()
        monitor = StreamMonitor(obs_client, config, stream_start_time, session_count)
        monitor_thread = threading.Thread(target=monitor.run, daemon=True)
        monitor_thread.start()
        print("Stream monitor started")
    
    # 11. Return success with stream URL
    channel_handle = "@robertfloyddugger4516"
    stream_url = build_youtube_stream_url(channel_handle)
    
    return {
        "success": True,
        "stream_url": stream_url,
        "game": config.get("game"),
        "title": final_title,
        "monitor_running": enable_monitor,
        "session_count": session_count
    }


def start_test_stream(
    game_name: str,
    test_mode: str,
    repo_path: Optional[str] = None
) -> dict:
    """
    unlisted: Normal stream, YouTube privacy set to unlisted.
              Auto-ends after 120 seconds.
              Full end-to-end test with real YouTube.
    
    youtube_test: Uses YOUTUBE_TEST_STREAM_KEY from .env.
                  YouTube's native test stream — never appears publicly.
                  Auto-ends after 120 seconds.
    
    virtual_camera: Starts OBS virtual camera output only.
                    No streaming. Preview overlays in any webcam app.
                    Does not auto-end — manual stop required.
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
    
    # 3. Handle test modes
    if test_mode == "virtual_camera":
        # Virtual camera mode - no YouTube, just OBS virtual camera
        obs_exe_path = os.getenv("OBS_EXE_PATH")
        if not ensure_obs_running(obs_exe_path):
            return {
                "success": False,
                "error": "Failed to ensure OBS is running"
            }
        
        obs_client = connect_obs()
        if not obs_client:
            return {
                "success": False,
                "error": "Failed to connect to OBS"
            }
        
        # Start virtual camera
        try:
            obs_client.call("StartVirtualCam")
            print("Started OBS virtual camera")
            return {
                "success": True,
                "test_mode": "virtual_camera",
                "game": config.get("game"),
                "note": "Virtual camera active - manual stop required"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to start virtual camera: {e}"
            }
    
    elif test_mode == "youtube_test":
        # YouTube test mode - use test stream key
        test_stream_key = os.getenv("YOUTUBE_TEST_STREAM_KEY")
        if not test_stream_key:
            return {
                "success": False,
                "error": "YOUTUBE_TEST_STREAM_KEY not found in environment"
            }
        
        # Override stream key for test
        original_stream_key = os.getenv("YOUTUBE_STREAM_KEY")
        os.environ["YOUTUBE_STREAM_KEY"] = test_stream_key
        
        # Start stream with unlisted privacy
        result = start_stream(
            game_name,
            privacy="unlisted",
            enable_monitor=False  # Disable monitoring for test
        )
        
        # Restore original stream key
        if original_stream_key:
            os.environ["YOUTUBE_STREAM_KEY"] = original_stream_key
        
        if result["success"]:
            # Auto-end after 120 seconds
            print("Test stream will auto-end in 120 seconds")
            threading.Timer(120, lambda: stop_obs_stream(connect_obs())).start()
        
        return result
    
    elif test_mode == "unlisted":
        # Unlisted mode - normal stream but unlisted privacy
        result = start_stream(
            game_name,
            privacy="unlisted",
            enable_monitor=False  # Disable monitoring for test
        )
        
        if result["success"]:
            # Auto-end after 120 seconds
            print("Test stream will auto-end in 120 seconds")
            threading.Timer(120, lambda: stop_obs_stream(connect_obs())).start()
        
        return result
    
    else:
        return {
            "success": False,
            "error": f"Invalid test_mode: {test_mode}. Must be unlisted, youtube_test, or virtual_camera"
        }


def main() -> None:
    """
    CLI: python stream_launcher.py <game_name> [--title "..."] [--private] [--no-monitor]
    
    Examples:
      python stream_launcher.py dorfromantik
      python stream_launcher.py "Scritchy Scratchy" --title "First look"
      python stream_launcher.py dorfromantik --no-monitor
    
    Prints: "Live at youtube.com/@robertfloyddugger4516"
    """
    if len(sys.argv) < 2:
        print("Usage: python stream_launcher.py <game_name> [--title \"...\"] [--private] [--no-monitor]")
        print("Example: python stream_launcher.py dorfromantik")
        sys.exit(1)
    
    game_name = sys.argv[1]
    title = None
    privacy = "public"
    enable_monitor = True
    
    # Parse optional arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--title" and i + 1 < len(sys.argv):
            title = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--private":
            privacy = "private"
            i += 1
        elif sys.argv[i] == "--no-monitor":
            enable_monitor = False
            i += 1
        else:
            print(f"Unknown argument: {sys.argv[i]}")
            sys.exit(1)
    
    result = start_stream(game_name, title=title, privacy=privacy, enable_monitor=enable_monitor)
    
    if not result["success"]:
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    print(f"Live at {result['stream_url']}")
    
    # If monitor is running, keep main thread alive and handle graceful shutdown
    if enable_monitor:
        print("Press Ctrl+C to stop the stream...")
        
        def signal_handler(sig, frame):
            """Handle Ctrl+C for graceful shutdown."""
            print("\nStream ended by user")
            # OBS will be stopped by monitor thread when it detects game closed
            # or we can force stop here if needed
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStream ended by user")
            sys.exit(0)


if __name__ == "__main__":
    main()
