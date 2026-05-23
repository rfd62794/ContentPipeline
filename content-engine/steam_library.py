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
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
    last_played: Optional[int] = None  # Unix timestamp from Steam API
    # Store API metadata
    genres: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    developers: List[str] = field(default_factory=list)
    publishers: List[str] = field(default_factory=list)
    release_date: Optional[str] = None
    header_image: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)


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
                'playtime_forever': game.get('playtime_forever', 0),  # in minutes
                'rtime_last_played': game.get('rtime_last_played')  # Unix timestamp
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
# Steam Store API Client
# =============================================================================

class SteamStoreAPIError(Exception):
    """Base exception for Steam Store API errors."""
    pass


class SteamStoreAPI:
    """Client for Steam Store API calls with rate limiting and caching."""
    
    BASE_URL = "https://store.steampowered.com/api"
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        requests_per_second: float = 10.0
    ):
        """
        Initialize Steam Store API client.
        
        Args:
            cache_dir: Directory for caching API responses. Defaults to .steam_cache/
            requests_per_second: Rate limit for API calls (default: 10 req/s)
        """
        if cache_dir is None:
            cache_dir = Path(".steam_cache")
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
        self.min_request_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
    
    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_cache_path(self, appid: int) -> Path:
        """Get cache file path for a given appid."""
        return self.cache_dir / f"{appid}.json"
    
    def _read_cache(self, appid: int) -> Optional[Dict[str, Any]]:
        """Read cached data for an appid."""
        cache_path = self._get_cache_path(appid)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read cache for {appid}: {e}")
            return None
    
    def _write_cache(self, appid: int, data: Dict[str, Any]) -> None:
        """Write data to cache for an appid."""
        cache_path = self._get_cache_path(appid)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to write cache for {appid}: {e}")
    
    def get_app_details(self, appid: int, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get detailed app information from Steam Store API.
        
        Args:
            appid: Steam app ID.
            use_cache: Whether to use cached data if available.
        
        Returns:
            Dictionary with app details, or None if not found.
        
        API Reference:
            https://store.steampowered.com/api/appdetails
        """
        # Check cache first
        if use_cache:
            cached = self._read_cache(appid)
            if cached:
                logger.debug(f"Using cached data for appid {appid}")
                return cached
        
        # Rate limit
        self._rate_limit()
        
        # Make request
        url = f"{self.BASE_URL}/appdetails"
        params = {
            'appids': appid,
            'l': 'english'  # Request English language data
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check if appid exists in response
            if str(appid) not in data:
                logger.warning(f"Appid {appid} not found in Store API response")
                return None
            
            app_data = data[str(appid)]
            
            # Check if request was successful
            if not app_data.get('success', False):
                logger.warning(f"Store API returned success=False for appid {appid}")
                return None
            
            # Extract the actual data
            details = app_data.get('data', {})
            
            # Cache the result
            if use_cache:
                self._write_cache(appid, details)
            
            return details
            
        except requests.RequestException as e:
            logger.error(f"Store API request failed for appid {appid}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid JSON response for appid {appid}: {e}")
            return None
    
    def parse_app_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Store API details into a standardized format.
        
        Args:
            details: Raw Store API response data.
        
        Returns:
            Dictionary with standardized fields.
        """
        parsed = {}
        
        # Basic info
        parsed['name'] = details.get('name', '')
        parsed['short_description'] = details.get('short_description', '')
        parsed['detailed_description'] = details.get('detailed_description', '')
        
        # Strip HTML from description
        import re
        html_tags = re.compile('<.*?>')
        parsed['description'] = html_tags.sub('', parsed['short_description'])
        
        # Developers and publishers
        parsed['developers'] = details.get('developers', [])
        parsed['publishers'] = details.get('publishers', [])
        
        # Release date
        release_date = details.get('release_date', {})
        parsed['release_date'] = release_date.get('date', '')
        
        # Genres
        genres = details.get('genres', [])
        parsed['genres'] = [g.get('description', '') for g in genres]
        
        # Tags (Steam tags)
        tags = details.get('steamspy_tags', [])
        if not tags:
            # Alternative tag location
            tags = details.get('tags', [])
            if tags:
                tags = [t.get('tag', '') for t in tags]
        parsed['tags'] = tags
        
        # Media
        parsed['header_image'] = details.get('header_image', '')
        
        screenshots = details.get('screenshots', [])
        parsed['screenshots'] = [s.get('path_full', '') for s in screenshots]
        
        # Price (if available)
        price_overview = details.get('price_overview', {})
        if price_overview:
            parsed['price'] = price_overview.get('final_formatted', '')
            parsed['discount_percent'] = price_overview.get('discount_percent', 0)
        else:
            parsed['price'] = 'Free to Play' if details.get('is_free', False) else 'N/A'
            parsed['discount_percent'] = 0
        
        return parsed
    
    def get_parsed_app_details(self, appid: int, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get parsed app details in a standardized format.
        
        Args:
            appid: Steam app ID.
            use_cache: Whether to use cached data if available.
        
        Returns:
            Dictionary with standardized app details, or None if not found.
        """
        details = self.get_app_details(appid, use_cache)
        if not details:
            return None
        
        return self.parse_app_details(details)


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
        steam_id: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        enable_store_api: bool = True
    ):
        """
        Initialize SteamLibrary.
        
        Args:
            steam_path: Path to Steam installation directory.
            api_key: Steam API key. If None, reads from STEAM_API_KEY env var.
            steam_id: Steam user ID. If None, reads from STEAM_ID env var.
            cache_dir: Directory for caching Store API responses.
            enable_store_api: Whether to enable Store API integration.
        """
        self.steam_path = steam_path
        self.api_client: Optional[SteamWebAPI] = None
        self.store_api_client: Optional[SteamStoreAPI] = None
        
        try:
            self.api_client = SteamWebAPI(api_key, steam_id)
        except SteamWebAPIError as e:
            logger.warning(f"Steam Web API not available: {e}")
        
        if enable_store_api:
            try:
                self.store_api_client = SteamStoreAPI(cache_dir=cache_dir)
            except Exception as e:
                logger.warning(f"Steam Store API not available: {e}")
    
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
                playtime_hours=playtime_hours,
                last_played=web.get('rtime_last_played')
            )
            library.append(game)
        
        # Sort by name
        library.sort(key=lambda g: g.name.lower())
        
        return library
    
    def get_library_with_metadata(self, limit: Optional[int] = None) -> List[GameInfo]:
        """
        Get merged library with Store API metadata.
        
        Args:
            limit: Maximum number of games to fetch metadata for (None = all).
        
        Returns:
            List of GameInfo objects with full Store API metadata.
        """
        library = self.get_library()
        
        if not self.store_api_client:
            logger.warning("Store API not available, returning basic library")
            return library
        
        # Limit the number of games to fetch metadata for
        games_to_enrich = library[:limit] if limit else library
        
        for game in games_to_enrich:
            try:
                details = self.store_api_client.get_parsed_app_details(game.appid)
                if details:
                    game.genres = details.get('genres', [])
                    game.tags = details.get('tags', [])
                    game.description = details.get('description', '')
                    game.developers = details.get('developers', [])
                    game.publishers = details.get('publishers', [])
                    game.release_date = details.get('release_date', '')
                    game.header_image = details.get('header_image', '')
                    game.screenshots = details.get('screenshots', [])
            except Exception as e:
                logger.warning(f"Failed to fetch metadata for {game.name} (appid {game.appid}): {e}")
        
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
                    playtime_hours=playtime_hours,
                    last_played=web.get('rtime_last_played')
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


def print_game_metadata(game: GameInfo) -> None:
    """
    Print detailed metadata for a single game.
    
    Args:
        game: GameInfo object with metadata.
    """
    print(f"\n{'='*60}")
    print(f"Game: {game.name}")
    print(f"AppID: {game.appid}")
    print(f"{'='*60}")
    
    if game.installed:
        print(f"Status: INSTALLED")
        if game.installdir:
            print(f"Install Dir: {game.installdir}")
    else:
        print(f"Status: Not Installed")
    
    if game.playtime_hours > 0:
        print(f"Playtime: {game.playtime_hours:.1f} hours")
    
    if game.genres:
        print(f"Genres: {', '.join(game.genres)}")
    
    if game.tags:
        print(f"Tags: {', '.join(game.tags[:10])}")  # Show first 10 tags
        if len(game.tags) > 10:
            print(f"       ... and {len(game.tags) - 10} more")
    
    if game.developers:
        print(f"Developers: {', '.join(game.developers)}")
    
    if game.publishers:
        print(f"Publishers: {', '.join(game.publishers)}")
    
    if game.release_date:
        print(f"Release Date: {game.release_date}")
    
    if game.description:
        # Truncate description if too long
        desc = game.description[:200] + "..." if len(game.description) > 200 else game.description
        print(f"Description: {desc}")
    
    if game.header_image:
        print(f"Header Image: {game.header_image}")
    
    if game.screenshots:
        print(f"Screenshots: {len(game.screenshots)} available")
        for i, ss in enumerate(game.screenshots[:3], 1):
            print(f"  {i}. {ss}")
        if len(game.screenshots) > 3:
            print(f"  ... and {len(game.screenshots) - 3} more")


# =============================================================================
# Query Functions
# =============================================================================

def load_cached_games() -> List[GameInfo]:
    """Load all cached game data from .steam_cache directory."""
    cache_dir = Path('.steam_cache')
    if not cache_dir.exists():
        return []
    
    games = []
    for cache_file in cache_dir.glob('*.json'):
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Parse basic game info from cache
            game = GameInfo(
                appid=data.get('steam_appid', 0),
                name=data.get('name', 'Unknown'),
                genres=data.get('genres', []),
                tags=data.get('tags', [])
            )
            games.append(game)
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load cache file {cache_file}: {e}")
    
    return games


def query_installed_by_playtime(min_hours: float) -> List[Dict[str, Any]]:
    """
    Query installed games with playtime >= min_hours.
    
    Args:
        min_hours: Minimum playtime threshold in hours.
    
    Returns:
        List of game dicts with name, playtime_hours, genres.
    """
    cache_dir = Path('.steam_cache')
    if not cache_dir.exists():
        return []
    
    # Load library to get playtime data
    library = SteamLibrary()
    full_library = library.get_library()
    
    # Filter installed games by playtime
    results = []
    for game in full_library:
        if game.installed and game.playtime_hours >= min_hours:
            # Load genres from cache if available
            cache_file = cache_dir / f"{game.appid}.json"
            genres = []
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        raw_genres = data.get('genres', [])
                        # Handle both string and dict formats
                        genres = [g if isinstance(g, str) else g.get('description', str(g)) for g in raw_genres]
                except (IOError, json.JSONDecodeError):
                    pass
            
            results.append({
                'name': game.name,
                'playtime_hours': game.playtime_hours,
                'genres': genres
            })
    
    # Sort by playtime descending
    results.sort(key=lambda x: x['playtime_hours'], reverse=True)
    return results


def query_recent_plays(days: int) -> List[Dict[str, Any]]:
    """
    Query games played within the last N days.
    
    Args:
        days: Number of days to look back.
    
    Returns:
        List of game dicts with name, last_played, playtime_hours.
    """
    # Calculate cutoff timestamp
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    
    # Load library to get last_played data
    library = SteamLibrary()
    full_library = library.get_library()
    
    results = []
    for game in full_library:
        if game.last_played and game.last_played >= cutoff_time:
            last_played_date = datetime.fromtimestamp(game.last_played).strftime('%Y-%m-%d')
            results.append({
                'name': game.name,
                'last_played': last_played_date,
                'playtime_hours': game.playtime_hours
            })
    
    # Sort by last_played descending
    results.sort(key=lambda x: x['last_played'], reverse=True)
    return results


def query_genre_breakdown() -> List[Dict[str, Any]]:
    """
    Aggregate total playtime by genre across all owned games.
    
    Returns:
        List of genre dicts with genre, total_hours, game_count.
    """
    cache_dir = Path('.steam_cache')
    if not cache_dir.exists():
        return []
    
    # Load library to get playtime data
    library = SteamLibrary()
    full_library = library.get_library()
    
    # Create game playtime lookup
    game_playtime = {game.appid: game.playtime_hours for game in full_library}
    
    # Aggregate by genre
    genre_hours = {}
    genre_counts = {}
    
    for cache_file in cache_dir.glob('*.json'):
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            appid = data.get('steam_appid', 0)
            playtime = game_playtime.get(appid, 0)
            raw_genres = data.get('genres', [])
            # Handle both string and dict formats
            genres = [g if isinstance(g, str) else g.get('description', str(g)) for g in raw_genres]
            
            for genre in genres:
                genre_hours[genre] = genre_hours.get(genre, 0) + playtime
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        except (IOError, json.JSONDecodeError):
            pass
    
    # Convert to results list
    results = []
    for genre, total_hours in genre_hours.items():
        results.append({
            'genre': genre,
            'total_hours': total_hours,
            'game_count': genre_counts.get(genre, 0)
        })
    
    # Sort by total hours descending
    results.sort(key=lambda x: x['total_hours'], reverse=True)
    return results


def handle_query(args, library: SteamLibrary) -> None:
    """Handle query commands."""
    if args.query == 'installed-by-playtime':
        if not args.min_hours:
            print("Error: --min-hours required for installed-by-playtime query")
            return
        
        results = query_installed_by_playtime(args.min_hours)
        if not results:
            print(f"No installed games with >= {args.min_hours} hours playtime")
            return
        
        print(f"\n=== Installed Games with >= {args.min_hours} Hours Playtime ===")
        for game in results:
            genres_str = ', '.join(game['genres'][:3]) if game['genres'] else 'N/A'
            print(f"{game['name']}: {game['playtime_hours']:.1f} hours | Genres: {genres_str}")
    
    elif args.query == 'recent-plays':
        if not args.days:
            print("Error: --days required for recent-plays query")
            return
        
        results = query_recent_plays(args.days)
        if not results:
            print(f"No games played in the last {args.days} days")
            return
        
        print(f"\n=== Games Played in Last {args.days} Days ===")
        for game in results:
            print(f"{game['name']}: {game['last_played']} | {game['playtime_hours']:.1f} hours")
    
    elif args.query == 'genre-breakdown':
        results = query_genre_breakdown()
        if not results:
            print("No genre data available")
            return
        
        print("\n=== Genre Breakdown by Total Playtime ===")
        for genre in results[:10]:  # Top 10
            print(f"{genre['genre']}: {genre['total_hours']:.1f} hours ({genre['game_count']} games)")


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
    parser.add_argument(
        '--metadata',
        action='store_true',
        help='Fetch full metadata from Steam Store API (slower, requires API calls)'
    )
    parser.add_argument(
        '--metadata-limit',
        type=int,
        metavar='N',
        default=None,
        help='Limit metadata fetching to N games (default: all)'
    )
    parser.add_argument(
        '--app-id',
        type=int,
        metavar='APPID',
        default=None,
        help='Show detailed metadata for a specific app ID'
    )
    parser.add_argument(
        '--query',
        type=str,
        metavar='QUERY_TYPE',
        default=None,
        choices=['installed-by-playtime', 'recent-plays', 'genre-breakdown'],
        help='Run query on cached data: installed-by-playtime, recent-plays, genre-breakdown'
    )
    parser.add_argument(
        '--min-hours',
        type=float,
        metavar='HOURS',
        default=None,
        help='Minimum playtime threshold for installed-by-playtime query'
    )
    parser.add_argument(
        '--days',
        type=int,
        metavar='DAYS',
        default=None,
        help='Number of days for recent-plays query'
    )
    
    args = parser.parse_args()
    
    # Initialize library
    library = SteamLibrary(steam_path=args.steam_path)
    
    # Handle single app ID lookup
    if args.app_id:
        if not library.store_api_client:
            print("Error: Store API not available")
            return
        
        details = library.store_api_client.get_parsed_app_details(args.app_id)
        if details:
            # Create a GameInfo object for display
            game = GameInfo(
                appid=args.app_id,
                name=details.get('name', 'Unknown'),
                genres=details.get('genres', []),
                tags=details.get('tags', []),
                description=details.get('description', ''),
                developers=details.get('developers', []),
                publishers=details.get('publishers', []),
                release_date=details.get('release_date', ''),
                header_image=details.get('header_image', ''),
                screenshots=details.get('screenshots', [])
            )
            print_game_metadata(game)
        else:
            print(f"Error: Could not fetch details for app ID {args.app_id}")
        return
    
    # Handle query commands
    if args.query:
        handle_query(args, library)
        return
    
    # Fetch games
    if args.metadata:
        games = library.get_library_with_metadata(limit=args.metadata_limit)
        print(f"\n=== Steam Library with Store API Metadata ===\n")
    elif args.recent is not None:
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
    
    # If metadata was fetched, show details for installed games
    if args.metadata:
        installed_with_metadata = [g for g in games if g.installed and g.genres]
        if installed_with_metadata:
            print(f"\n=== Installed Games with Metadata ===\n")
            for game in installed_with_metadata:
                print_game_metadata(game)


if __name__ == "__main__":
    main()
