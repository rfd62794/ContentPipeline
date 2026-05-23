"""
Game Metrics - Enriches Steam library data with SteamSpy and YouTube content metrics

Combines Steam library data with SteamSpy market data and YouTube search data to provide
comprehensive content demand signals for game selection and prioritization.

Three dimensions per game:
- Your playtime (personal signal)
- SteamSpy players_2weeks (market signal)  
- YouTube content demand (content signal)
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

# Steam library imports
from steam_library import SteamLibrary, GameInfo, get_installed_games

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.auth import default
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: Google API libraries not installed.")
    print("Run: pip install google-auth google-auth-oauthlib google-api-python-client")
    sys.exit(1)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class GameMetrics:
    """Combined Steam, SteamSpy, and YouTube metrics for a game."""
    appid: int
    name: str
    playtime_hours: float
    steam_active_players: Optional[int]
    players_2weeks: Optional[int]
    owners_estimate: Optional[str]
    review_score: Optional[float]
    top_video_views: int
    recent_upload_count: int
    avg_views_top5: float
    content_demand_score: float
    genres: List[str]
    last_played: Optional[int]


# =============================================================================
# Pure Functions (Testable Without Network)
# =============================================================================

def compute_content_demand_score(top_views: int) -> float:
    """
    Compute content demand score from top video views.
    
    Score is (top_video_views / 1000) capped at 100.
    
    Args:
        top_views: Highest view count in search results
        
    Returns:
        Content demand score (0-100)
    """
    score = top_views / 1000.0
    return min(score, 100.0)


def parse_steamspy_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse SteamSpy API response into clean metrics.
    
    Args:
        raw: Raw SteamSpy API response
        
    Returns:
        Dict with players_2weeks, owners_estimate, positive_reviews, negative_reviews
    """
    return {
        'players_2weeks': raw.get('players_2weeks', 0),
        'owners_estimate': raw.get('owners', '0 .. 0'),
        'positive_reviews': raw.get('positive', 0),
        'negative_reviews': raw.get('negative', 0)
    }


def compute_review_score(positive: int, negative: int) -> Optional[float]:
    """
    Compute review score from positive and negative review counts.
    
    Args:
        positive: Number of positive reviews
        negative: Number of negative reviews
        
    Returns:
        Review score as percentage (0-100), or None if no reviews
    """
    total = positive + negative
    if total == 0:
        return None
    return (positive / total) * 100.0


def merge_game_metrics(steam_data: GameInfo, steamspy_data: Dict[str, Any], youtube_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge Steam game data with SteamSpy and YouTube search metrics.
    
    Args:
        steam_data: GameInfo from Steam library
        steamspy_data: SteamSpy metrics dict with players_2weeks, owners_estimate, etc.
        youtube_data: YouTube metrics dict with top_video_views, recent_upload_count, avg_views_top5
        
    Returns:
        Merged metrics dict
    """
    content_demand_score = compute_content_demand_score(youtube_data.get('top_video_views', 0))
    review_score = compute_review_score(
        steamspy_data.get('positive_reviews', 0),
        steamspy_data.get('negative_reviews', 0)
    )
    
    return {
        'appid': steam_data.appid,
        'name': steam_data.name,
        'playtime_hours': steam_data.playtime_hours,
        'steam_active_players': steam_data.steam_active_players if hasattr(steam_data, 'steam_active_players') else None,
        'players_2weeks': steamspy_data.get('players_2weeks'),
        'owners_estimate': steamspy_data.get('owners_estimate'),
        'review_score': review_score,
        'top_video_views': youtube_data.get('top_video_views', 0),
        'recent_upload_count': youtube_data.get('recent_upload_count', 0),
        'avg_views_top5': youtube_data.get('avg_views_top5', 0.0),
        'content_demand_score': content_demand_score,
        'genres': steam_data.genres if hasattr(steam_data, 'genres') else [],
        'last_played': steam_data.last_played
    }


def filter_by_playtime(games: List[Dict[str, Any]], min_hours: float) -> List[Dict[str, Any]]:
    """
    Filter games by minimum playtime threshold.
    
    Args:
        games: List of game metrics dicts
        min_hours: Minimum playtime hours
        
    Returns:
        Filtered list of games
    """
    return [game for game in games if game['playtime_hours'] >= min_hours]


def filter_installed(games: List[Dict[str, Any]], installed_appids: set) -> List[Dict[str, Any]]:
    """
    Filter to only installed games.
    
    Args:
        games: List of game metrics dicts
        installed_appids: Set of installed appids
        
    Returns:
        Filtered list of installed games
    """
    return [game for game in games if game['appid'] in installed_appids]


def sort_by_metric(games: List[Dict[str, Any]], metric: str, descending: bool = True) -> List[Dict[str, Any]]:
    """
    Sort games by specified metric.
    
    Args:
        games: List of game metrics dicts
        metric: Metric key to sort by
        descending: Sort order (default True for descending)
        
    Returns:
        Sorted list of games
    """
    return sorted(games, key=lambda x: x.get(metric, 0), reverse=descending)


def format_metrics_table(games: List[Dict[str, Any]]) -> str:
    """
    Format game metrics as a readable table.
    
    Args:
        games: List of game metrics dicts
        
    Returns:
        Formatted table string
    """
    if not games:
        return "No games to display."
    
    lines = []
    lines.append("=" * 150)
    lines.append(f"{'Name':<30} {'Playtime':<10} {'2Wk Players':<12} {'Owners':<15} {'Review':<8} {'Top Views':<12} {'Recent':<8} {'Demand':<8}")
    lines.append("=" * 150)
    
    for game in games:
        name = game['name'][:27] + '...' if len(game['name']) > 30 else game['name']
        playtime = f"{game['playtime_hours']:.1f}h"
        players_2weeks = f"{game['players_2weeks'] or 0:,}" if game['players_2weeks'] else "N/A"
        owners = game['owners_estimate'][:12] + '...' if len(game.get('owners_estimate', '')) > 15 else game.get('owners_estimate', 'N/A')
        review = f"{game['review_score']:.1f}%" if game['review_score'] is not None else "N/A"
        top_views = f"{game['top_video_views']:,}"
        recent = str(game['recent_upload_count'])
        demand = f"{game['content_demand_score']:.1f}"
        
        lines.append(f"{name:<30} {playtime:<10} {players_2weeks:<12} {owners:<15} {review:<8} {top_views:<12} {recent:<8} {demand:<8}")
    
    lines.append("=" * 150)
    return "\n".join(lines)


# =============================================================================
# API Client
# =============================================================================

class GameMetricsClient:
    """Client for enriching Steam library data with SteamSpy and YouTube search metrics."""
    
    SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
    TOKEN_FILE = ".youtube_token.json"
    CLIENT_SECRET_FILE = "client_secret.json"
    CACHE_FILE = ".youtube_cache/game_metrics.json"
    STEAMSPY_API_URL = "https://steamspy.com/api.php"
    STEAMSPY_CACHE_DIR = ".steam_cache"
    RATE_LIMIT_DELAY = 2.0  # 2 seconds between API calls to respect quota
    STEAMSPY_RATE_LIMIT_DELAY = 1.0  # 1 second between SteamSpy calls
    
    def __init__(self, client_secret_path: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        Initialize GameMetrics client.
        
        Args:
            client_secret_path: Path to client_secret.json
            cache_dir: Directory for cache (default: .youtube_cache)
        """
        self.credentials = None
        self.youtube_service = None
        self.cache_dir = Path(cache_dir) if cache_dir else Path(".youtube_cache")
        self.cache_file = self.cache_dir / "game_metrics.json"
        
        # Determine client secret path
        if client_secret_path:
            self.client_secret_path = client_secret_path
        else:
            self.client_secret_path = self.CLIENT_SECRET_FILE
        
        # Load credentials
        self._load_credentials()
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_credentials(self):
        """Load OAuth credentials using gcloud Application Default Credentials (ADC)."""
        # Use gcloud ADC for authentication (same pattern as youtube_upload.py)
        try:
            credentials, project = default(
                scopes=["https://www.googleapis.com/auth/youtube.readonly"]
            )
            self.credentials = credentials
        except Exception as e:
            raise RuntimeError("Google ADC credentials not found. Run: gcloud auth application-default login")
        
        # Build YouTube service
        self.youtube_service = build('youtube', 'v3', credentials=self.credentials)
        
        # Create SteamSpy cache directory
        self.steamspy_cache_dir = Path(self.STEAMSPY_CACHE_DIR)
        self.steamspy_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_steamspy_data(self, appid: int) -> Dict[str, Any]:
        """
        Fetch SteamSpy data for a specific game.
        
        Args:
            appid: Steam app ID
            
        Returns:
            Dict with players_2weeks, owners_estimate, positive_reviews, negative_reviews
        """
        cache_file = self.steamspy_cache_dir / f"spy_{appid}.json"
        
        # Check cache first
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    # Cache is valid for 24 hours
                    cache_time = datetime.fromisoformat(cached_data.get('timestamp', '1970-01-01'))
                    if (datetime.now() - cache_time).total_seconds() < 86400:  # 24 hours
                        return parse_steamspy_response(cached_data)
            except (IOError, json.JSONDecodeError):
                pass
        
        # Fetch from SteamSpy API
        try:
            params = {'request': 'appdetails', 'appid': appid}
            response = requests.get(self.STEAMSPY_API_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Add timestamp and cache
            data['timestamp'] = datetime.now().isoformat()
            try:
                with open(cache_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except IOError as e:
                print(f"Warning: Could not cache SteamSpy data for appid {appid}: {e}")
            
            # Rate limiting
            time.sleep(self.STEAMSPY_RATE_LIMIT_DELAY)
            
            return parse_steamspy_response(data)
            
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"SteamSpy API error for appid {appid}: {e}")
            return {
                'players_2weeks': 0,
                'owners_estimate': '0 .. 0',
                'positive_reviews': 0,
                'negative_reviews': 0
            }
    
    def search_youtube_for_game(self, game_name: str, max_results: int = 5, days_back: int = 90) -> Dict[str, Any]:
        """
        Search YouTube for gameplay videos of a specific game.
        
        Args:
            game_name: Name of the game to search for
            max_results: Maximum number of results to return
            days_back: Only include videos published within this many days
            
        Returns:
            Dict with top_video_views, recent_upload_count, avg_views_top5
        """
        query = f"{game_name} gameplay"
        published_after = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
        
        try:
            search_response = self.youtube_service.search().list(
                q=query,
                part='id,snippet',
                maxResults=max_results,
                order='viewCount',
                publishedAfter=published_after,
                type='video'
            ).execute()
            
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            if not video_ids:
                # Rate limiting even for empty results
                time.sleep(self.RATE_LIMIT_DELAY)
                return {
                    'top_video_views': 0,
                    'recent_upload_count': 0,
                    'avg_views_top5': 0.0
                }
            
            # Get video statistics
            videos_response = self.youtube_service.videos().list(
                part='statistics',
                id=','.join(video_ids)
            ).execute()
            
            view_counts = []
            for video in videos_response.get('items', []):
                views = int(video['statistics'].get('viewCount', 0))
                view_counts.append(views)
            
            if view_counts:
                top_video_views = max(view_counts)
                recent_upload_count = len(view_counts)
                avg_views_top5 = sum(view_counts) / len(view_counts)
            else:
                top_video_views = 0
                recent_upload_count = 0
                avg_views_top5 = 0.0
            
            # Rate limiting
            time.sleep(self.RATE_LIMIT_DELAY)
            
            return {
                'top_video_views': top_video_views,
                'recent_upload_count': recent_upload_count,
                'avg_views_top5': avg_views_top5
            }
            
        except HttpError as e:
            safe_name = game_name.encode('ascii', 'ignore').decode('ascii') if game_name else 'Unknown'
            print(f"YouTube API error for {safe_name}: {e}")
            # Check if it's a quota error - if so, wait longer
            if 'quota' in str(e).lower() or 'ratelimit' in str(e).lower():
                print("Quota limit hit, waiting 60 seconds...")
                time.sleep(60)  # Wait longer for quota errors
            else:
                # Rate limiting even for other errors
                time.sleep(self.RATE_LIMIT_DELAY)
            return {
                'top_video_views': 0,
                'recent_upload_count': 0,
                'avg_views_top5': 0.0
            }
    
    def load_cache(self) -> Dict[str, Any]:
        """Load cached metrics from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError):
                pass
        return {}
    
    def save_cache(self, cache_data: Dict[str, Any]):
        """Save metrics to cache file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cache: {e}")
    
    def get_game_metrics(self, steam_library: SteamLibrary, refresh: bool = False, 
                         installed_only: bool = False, min_hours: Optional[float] = None,
                         limit: Optional[int] = None) -> List[GameMetrics]:
        """
        Get comprehensive metrics for Steam library games.
        
        Args:
            steam_library: SteamLibrary instance
            refresh: Force refresh of YouTube data (ignore cache)
            installed_only: Only include installed games
            min_hours: Filter by minimum playtime hours
            limit: Limit to top N results by content demand score
            
        Returns:
            List of GameMetrics objects
        """
        # Load cache
        cache = self.load_cache() if not refresh else {}
        
        # Get Steam library
        games = steam_library.get_library()
        
        # Apply filters
        if installed_only:
            installed_games = get_installed_games()
            installed_appids = {game.get('appid') for game in installed_games}
            games = [game for game in games if game.appid in installed_appids]
        
        if min_hours:
            games = [game for game in games if game.playtime_hours >= min_hours]
        
        # Enrich with SteamSpy and YouTube data
        metrics_list = []
        for game in games:
            appid_str = str(game.appid)
            
            # Fetch SteamSpy data (free API, no quota issues)
            print(f"Fetching SteamSpy data for: {game.name}")
            steamspy_data = self.fetch_steamspy_data(game.appid)
            
            # Check cache or fetch new YouTube data
            if appid_str in cache and not refresh:
                youtube_data = cache[appid_str]
            else:
                # Handle Unicode in game names for Windows console
                safe_name = game.name.encode('ascii', 'ignore').decode('ascii') if game.name else 'Unknown'
                print(f"Fetching YouTube data for: {safe_name}")
                youtube_data = self.search_youtube_for_game(game.name)
                cache[appid_str] = youtube_data
            
            # Merge metrics
            merged = merge_game_metrics(game, steamspy_data, youtube_data)
            metrics_list.append(merged)
        
        # Save cache
        self.save_cache(cache)
        
        # Convert to GameMetrics objects
        game_metrics = []
        for m in metrics_list:
            game_metrics.append(GameMetrics(
                appid=m['appid'],
                name=m['name'],
                playtime_hours=m['playtime_hours'],
                steam_active_players=m['steam_active_players'],
                players_2weeks=m['players_2weeks'],
                owners_estimate=m['owners_estimate'],
                review_score=m['review_score'],
                top_video_views=m['top_video_views'],
                recent_upload_count=m['recent_upload_count'],
                avg_views_top5=m['avg_views_top5'],
                content_demand_score=m['content_demand_score'],
                genres=m['genres'],
                last_played=m['last_played']
            ))
        
        # Sort by content demand score
        game_metrics.sort(key=lambda x: x.content_demand_score, reverse=True)
        
        # Apply limit
        if limit:
            game_metrics = game_metrics[:limit]
        
        return game_metrics


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Game Metrics - Steam library enriched with YouTube content demand signals')
    parser.add_argument('--all', action='store_true', help='Full library sorted by content_demand_score')
    parser.add_argument('--installed', action='store_true', help='Installed games only')
    parser.add_argument('--min-hours', type=float, metavar='HOURS', help='Filter by playtime threshold')
    parser.add_argument('--save', action='store_true', help='Write to .youtube_cache/game_metrics.json')
    parser.add_argument('--limit', type=int, metavar='N', help='Top N results only')
    parser.add_argument('--refresh', action='store_true', help='Refresh YouTube data (ignore cache)')
    parser.add_argument('--client-secret', type=str, help='Path to client_secret.json')
    
    args = parser.parse_args()
    
    # Initialize clients
    try:
        metrics_client = GameMetricsClient(client_secret_path=args.client_secret)
        steam_library = SteamLibrary()
    except Exception as e:
        print(f"Error initializing clients: {e}")
        sys.exit(1)
    
    # Get metrics
    metrics = metrics_client.get_game_metrics(
        steam_library=steam_library,
        refresh=args.refresh,
        installed_only=args.installed,
        min_hours=args.min_hours,
        limit=args.limit
    )
    
    # Display results
    print(format_metrics_table([m.__dict__ for m in metrics]))
    print(f"\nTotal games: {len(metrics)}")
    
    # Save if requested
    if args.save:
        cache_data = {str(m.appid): m.__dict__ for m in metrics}
        metrics_client.save_cache(cache_data)
        print(f"Saved to {metrics_client.cache_file}")


if __name__ == '__main__':
    main()