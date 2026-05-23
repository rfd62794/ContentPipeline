"""
Steam Library Detection System

Combines local ACF file parsing with Steam Web API to provide a complete
view of owned games, installation status, and playtime data.

Usage:
    python steam_library.py

Environment Variables:
    STEAM_API_KEY: Steam Web API key (required for Web API calls)
    STEAM_ID: Steam user ID (required for Web API calls)
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class GameInfo:
    """Unified game information from both local and web sources."""
    appid: int
    name: str
    installdir: Optional[str] = None
    installed: bool = False
    playtime_hours: float = 0.0


# =============================================================================
# Local ACF Parser (Pure Function)
# =============================================================================

def parse_acf_file(content: str) -> Dict[str, Any]:
    """
    Parse a Steam AppManifest.acf file content.
    
    ACF format is similar to INI but with nested sections:
        "AppState"
        {
            "appid"        "12345"
            "name"         "Game Name"
            "installdir"   "GameDirectory"
            ...
        }
    
    Args:
        content: Raw string content of an ACF file.
    
    Returns:
        Dictionary with parsed key-value pairs. Returns empty dict on parse error.
    
    Example:
        >>> content = '"AppState"\\n{\\n  "appid" "12345"\\n}'
        >>> parse_acf_file(content)
        {'appid': '12345'}
    """
    if not content:
        return {}
    
    result = {}
    stack = [result]
    
    # Pattern to match key-value pairs: "key" "value"
    kv_pattern = re.compile(r'^\s*"([^"]+)"\s*"([^"]*)"')
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('//'):
            continue
        
        # Opening brace - start new section
        if line == '{':
            new_section = {}
            current = stack[-1]
            # If the last key added was a section name, make it a dict
            if current and isinstance(current, dict):
                # Get the last key that was added (section name)
                # For simplicity, we'll just track the current context
                pass
            stack.append(new_section)
            continue
        
        # Closing brace - end section
        if line == '}':
            if len(stack) > 1:
                section = stack.pop()
                # Merge section into parent
                parent = stack[-1]
                if isinstance(parent, dict):
                    parent.update(section)
            continue
        
        # Key-value pair
        match = kv_pattern.match(line)
        if match:
            key, value = match.groups()
            current = stack[-1]
            if isinstance(current, dict):
                current[key] = value
    
    return result


def parse_acf_files(acf_dir: Path) -> List[Dict[str, Any]]:
    """
    Parse all ACF files in a directory.
    
    Args:
        acf_dir: Path to directory containing ACF files (e.g., steamapps/).
    
    Returns:
        List of parsed dictionaries, one per ACF file.
    """
    if not acf_dir.exists() or not acf_dir.is_dir():
        logger.warning(f"ACF directory does not exist: {acf_dir}")
        return []
    
    results = []
    for acf_file in acf_dir.glob("*.acf"):
        try:
            content = acf_file.read_text(encoding='utf-8', errors='ignore')
            parsed = parse_acf_file(content)
            if parsed:
                results.append(parsed)
        except Exception as e:
            logger.error(f"Failed to parse {acf_file}: {e}")
    
    return results


def get_installed_games(steam_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Get list of installed games from local Steam ACF files.
    
    Args:
        steam_path: Path to Steam installation directory.
                    Defaults to C:/Program Files (x86)/Steam
    
    Returns:
        List of dicts with keys: appid, name, installdir
    """
    if steam_path is None:
        steam_path = Path("C:/Program Files (x86)/Steam")
    
    steamapps_path = steam_path / "steamapps"
    if not steamapps_path.exists():
        logger.warning(f"Steam apps directory not found: {steamapps_path}")
        return []
    
    acf_files = parse_acf_files(steamapps_path)
    
    games = []
    for acf_data in acf_files:
        try:
            appid = int(acf_data.get('appid', 0))
            name = acf_data.get('name', 'Unknown')
            installdir = acf_data.get('installdir', '')
            
            if appid > 0:
                games.append({
                    'appid': appid,
                    'name': name,
                    'installdir': installdir
                })
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid ACF data: {acf_data}, error: {e}")
    
    return games


# =============================================================================
# Steam Web API Client
# =============================================================================

class SteamWebAPIError(Exception):
    """Base exception for Steam Web API errors."""
    pass


class SteamWebAPI:
    """Client for Steam Web API calls."""
    
    BASE_URL = "https://api.steampowered.com"
    
    def __init__(self, api_key: Optional[str] = None, steam_id: Optional[str] = None):
        """
        Initialize Steam Web API client.
        
        Args:
            api_key: Steam API key. If None, reads from STEAM_API_KEY env var.
            steam_id: Steam user ID. If None, reads from STEAM_ID env var.
        
        Raises:
            SteamWebAPIError: If API key or Steam ID is not available.
        """
        self.api_key = api_key or os.getenv('STEAM_API_KEY')
        self.steam_id = steam_id or os.getenv('STEAM_ID')
        
        if not self.api_key:
            raise SteamWebAPIError("STEAM_API_KEY not found in environment variables")
        if not self.steam_id:
            raise SteamWebAPIError("STEAM_ID not found in environment variables")
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to Steam Web API.
        
        Args:
            endpoint: API endpoint path (e.g., /IPlayerService/GetOwnedGames/v0001/)
            params: Query parameters.
        
        Returns:
            Parsed JSON response.
        
        Raises:
            SteamWebAPIError: On request failure or invalid response.
        """
        url = f"{self.BASE_URL}{endpoint}"
        params['key'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for Steam API errors
            if 'response' in data and 'error' in data['response']:
                raise SteamWebAPIError(f"Steam API error: {data['response']['error']}")
            
            return data
        except requests.RequestException as e:
            raise SteamWebAPIError(f"Request failed: {e}")
        except ValueError as e:
            raise SteamWebAPIError(f"Invalid JSON response: {e}")
    
    def get_owned_games(self, include_played_free_games: bool = False) -> List[Dict[str, Any]]:
        """
        Get all games owned by the user.
        
        Args:
            include_played_free_games: Include free games that have been played.
        
        Returns:
            List of game dicts with keys: appid, name, playtime_forever
        
        API Reference:
            https://steamcommunity.com/dev/doc/webapi/IPlayerService#GetOwnedGames
        """
        params = {
            'steamid': self.steam_id,
            'include_appinfo': 1,  # Include game names
            'include_played_free_games': 1 if include_played_free_games else 0,
        }
        
        data = self._make_request('/IPlayerService/GetOwnedGames/v0001/', params)
        
        games = []
        response = data.get('response', {})
        games_list = response.get('games', [])
        
        for game in games_list:
            games.append({
                'appid': game.get('appid'),
                'name': game.get('name', 'Unknown'),
                'playtime_forever': game.get('playtime_forever', 0)  # in minutes
            })
        
        return games
    
    def get_recently_played_games(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recently played games.
        
        Args:
            count: Maximum number of games to return.
        
        Returns:
            List of game dicts with keys: appid, name, playtime_2weeks, playtime_forever
        
        API Reference:
            https://steamcommunity.com/dev/doc/webapi/IPlayerService#GetRecentlyPlayedGames
        """
        params = {
            'steamid': self.steam_id,
            'count': count
        }
        
        data = self._make_request('/IPlayerService/GetRecentlyPlayedGames/v0001/', params)
        
        games = []
        response = data.get('response', {})
        games_list = response.get('games', [])
        
        for game in games_list:
            games.append({
                'appid': game.get('appid'),
                'name': game.get('name', 'Unknown'),
                'playtime_2weeks': game.get('playtime_2weeks', 0),  # in minutes
                'playtime_forever': game.get('playtime_forever', 0)  # in minutes
            })
        
        return games


# =============================================================================
# SteamLibrary Class
# =============================================================================

class SteamLibrary:
    """
    Merges local ACF data with Steam Web API data.
    
    Provides a unified view of the Steam library with installation status
    and playtime information.
    """
    
    def __init__(
        self,
        steam_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        steam_id: Optional[str] = None
    ):
        """
        Initialize SteamLibrary.
        
        Args:
            steam_path: Path to Steam installation directory.
            api_key: Steam API key. If None, reads from STEAM_API_KEY env var.
            steam_id: Steam user ID. If None, reads from STEAM_ID env var.
        """
        self.steam_path = steam_path
        self.api_client: Optional[SteamWebAPI] = None
        
        try:
            self.api_client = SteamWebAPI(api_key, steam_id)
        except SteamWebAPIError as e:
            logger.warning(f"Steam Web API not available: {e}")
    
    def get_library(self) -> List[GameInfo]:
        """
        Get merged library from both local and web sources.
        
        Returns:
            List of GameInfo objects with merged data.
        """
        # Get local installed games
        installed_games = get_installed_games(self.steam_path)
        installed_map = {g['appid']: g for g in installed_games}
        
        # Get web API games
        web_games = []
        if self.api_client:
            try:
                web_games = self.api_client.get_owned_games()
            except SteamWebAPIError as e:
                logger.error(f"Failed to fetch owned games: {e}")
        
        web_map = {g['appid']: g for g in web_games}
        
        # Merge data
        all_appids = set(installed_map.keys()) | set(web_map.keys())
        
        library = []
        for appid in all_appids:
            local = installed_map.get(appid, {})
            web = web_map.get(appid, {})
            
            # Prefer name from web API (more accurate), fall back to local
            name = web.get('name') or local.get('name', 'Unknown')
            
            # Convert playtime from minutes to hours
            playtime_minutes = web.get('playtime_forever', 0)
            playtime_hours = playtime_minutes / 60.0 if playtime_minutes else 0.0
            
            game = GameInfo(
                appid=appid,
                name=name,
                installdir=local.get('installdir'),
                installed=appid in installed_map,
                playtime_hours=playtime_hours
            )
            library.append(game)
        
        # Sort by name
        library.sort(key=lambda g: g.name.lower())
        
        return library
    
    def get_installed_only(self) -> List[GameInfo]:
        """Get only installed games."""
        return [g for g in self.get_library() if g.installed]
    
    def get_recently_played(self, count: int = 10) -> List[GameInfo]:
        """
        Get recently played games from Web API.
        
        Args:
            count: Maximum number of games to return.
        
        Returns:
            List of GameInfo objects.
        """
        if not self.api_client:
            logger.warning("Steam Web API not available")
            return []
        
        try:
            web_games = self.api_client.get_recently_played_games(count)
            installed_games = get_installed_games(self.steam_path)
            installed_map = {g['appid']: g for g in installed_games}
            
            library = []
            for web in web_games:
                appid = web['appid']
                local = installed_map.get(appid, {})
                
                playtime_minutes = web.get('playtime_forever', 0)
                playtime_hours = playtime_minutes / 60.0 if playtime_minutes else 0.0
                
                game = GameInfo(
                    appid=appid,
                    name=web.get('name', 'Unknown'),
                    installdir=local.get('installdir'),
                    installed=appid in installed_map,
                    playtime_hours=playtime_hours
                )
                library.append(game)
            
            return library
        except SteamWebAPIError as e:
            logger.error(f"Failed to fetch recently played games: {e}")
            return []


# =============================================================================
# CLI Interface
# =============================================================================

def print_library_table(library: List[GameInfo]) -> None:
    """
    Print library as a formatted table to terminal.
    
    Args:
        library: List of GameInfo objects.
    """
    if not library:
        print("No games found in library.")
        return
    
    # Calculate column widths
    max_name_len = max(len(g.name) for g in library)
    name_width = min(max_name_len, 50)  # Cap at 50 chars
    
    # Header
    print(f"{'Installed':<10} {'AppID':<10} {'Name':<{name_width}} {'Playtime (hrs)':<15}")
    print("-" * (10 + 10 + name_width + 15 + 3))
    
    # Rows
    for game in library:
        installed_marker = "[INSTALLED]" if game.installed else ""
        playtime_str = f"{game.playtime_hours:.1f}" if game.playtime_hours > 0 else "-"
        name_display = game.name[:name_width] if len(game.name) > name_width else game.name
        
        # Sanitize name for display (remove problematic Unicode)
        try:
            name_display.encode('ascii')
        except UnicodeEncodeError:
            name_display = name_display.encode('ascii', 'replace').decode('ascii')
        
        print(f"{installed_marker:<10} {game.appid:<10} {name_display:<{name_width}} {playtime_str:<15}")
    
    print(f"\nTotal games: {len(library)}")
    installed_count = sum(1 for g in library if g.installed)
    print(f"Installed: {installed_count}")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Steam Library Detection System")
    parser.add_argument(
        '--steam-path',
        type=Path,
        default=None,
        help='Path to Steam installation directory (default: C:/Program Files (x86)/Steam)'
    )
    parser.add_argument(
        '--installed-only',
        action='store_true',
        help='Show only installed games'
    )
    parser.add_argument(
        '--recent',
        type=int,
        metavar='N',
        default=None,
        help='Show recently played games (limit to N games)'
    )
    
    args = parser.parse_args()
    
    # Initialize library
    library = SteamLibrary(steam_path=args.steam_path)
    
    # Fetch games
    if args.recent is not None:
        games = library.get_recently_played(count=args.recent)
        print(f"\n=== Recently Played Games (Last {args.recent}) ===\n")
    elif args.installed_only:
        games = library.get_installed_only()
        print("\n=== Installed Games ===\n")
    else:
        games = library.get_library()
        print("\n=== Complete Steam Library ===\n")
    
    # Print table
    print_library_table(games)


if __name__ == "__main__":
    main()
