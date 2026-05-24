"""
YouTube Analytics Client

Pulls video performance metrics, retention curves, traffic sources, and channel stats
from YouTube Analytics API v2. Reuses OAuth authentication from youtube_library.py.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
from datetime import datetime, timedelta


# Google API imports
_google_api_available = False
_HttpError = None
try:
    from googleapiclient.errors import HttpError as _HttpError
    from core.youtube_auth import build_service
    _google_api_available = True
except ImportError:
    pass


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class VideoStats:
    """Video performance metrics."""
    video_id: str
    views: int
    watch_time_minutes: float
    avg_view_duration_seconds: float
    avg_view_percentage: float
    subscribers_gained: int
    likes: int
    start_date: str
    end_date: str


@dataclass
class RetentionPoint:
    """Retention curve data point."""
    elapsed_video_time_ratio: float  # 0.0 to 1.0 (start to end of video)
    audience_watch_ratio: float  # 0.0 to 1.0 (percentage of audience still watching)


@dataclass
class ChannelStats:
    """Channel performance metrics."""
    total_views: int
    watch_time_minutes: float
    subscribers_gained: int
    start_date: str
    end_date: str


# =============================================================================
# API Client
# =============================================================================

class YouTubeAnalytics:
    """Client for YouTube Analytics API v2."""
    
    SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]
    
    def __init__(self, client_secret_path: Optional[str] = None):
        """
        Initialize YouTube Analytics client using OAuth with refresh token.
        
        Args:
            client_secret_path: Path to client_secret.json. If not provided, looks in current directory.
        """
        if _google_api_available:
            self.service = build_service('youtubeAnalytics', 'v2', self.SCOPES)
        else:
            self.service = None
    
    def get_video_stats(self, video_id: str, start_date: str, end_date: str) -> Optional[VideoStats]:
        """
        Get video performance metrics.
        
        Args:
            video_id: YouTube video ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            VideoStats object or None if error.
        """
        if not _google_api_available or self.service is None:
            return None
        
        try:
            response = self.service.reports().query(
                ids=f'channel==MINE',
                dimensions='video',
                metrics='views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes',
                filters=f'video=={video_id}',
                startDate=start_date,
                endDate=end_date
            ).execute()
            
            if not response.get('rows'):
                return None
            
            row = response['rows'][0]
            
            return VideoStats(
                video_id=video_id,
                views=int(row[0]),
                watch_time_minutes=float(row[1]),
                avg_view_duration_seconds=float(row[2]),
                avg_view_percentage=float(row[3]),
                subscribers_gained=int(row[4]),
                likes=int(row[5]),
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            if _google_api_available and _HttpError and isinstance(e, _HttpError):
                print(f"Error fetching video stats: {e}")
            return None
    
    def get_retention_curve(self, video_id: str) -> List[RetentionPoint]:
        """
        Get retention curve data for a video.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            List of RetentionPoint objects.
        """
        if not _google_api_available or self.service is None:
            return []
        
        try:
            response = self.service.reports().query(
                ids=f'channel==MINE',
                dimensions='elapsedVideoTimeRatio,audienceWatchRatio',
                metrics='views',
                filters=f'video=={video_id}',
                sort='elapsedVideoTimeRatio'
            ).execute()
            
            points = []
            for row in response.get('rows', []):
                points.append(RetentionPoint(
                    elapsed_video_time_ratio=float(row[0]),
                    audience_watch_ratio=float(row[1])
                ))
            
            return points
        except Exception as e:
            if _google_api_available and _HttpError and isinstance(e, _HttpError):
                print(f"Error fetching retention curve: {e}")
            return []
    
    def get_traffic_sources(self, video_id: str) -> Dict[str, int]:
        """
        Get traffic sources for a video.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dictionary mapping source_type to view_count.
        """
        if not _google_api_available or self.service is None:
            return {}
        
        try:
            response = self.service.reports().query(
                ids=f'channel==MINE',
                dimensions='insightTrafficSourceType',
                metrics='views',
                filters=f'video=={video_id}'
            ).execute()
            
            sources = {}
            for row in response.get('rows', []):
                source_type = row[0]
                view_count = int(row[1])
                sources[source_type] = view_count
            
            return sources
        except Exception as e:
            if _google_api_available and _HttpError and isinstance(e, _HttpError):
                print(f"Error fetching traffic sources: {e}")
            return {}
    
    def get_channel_stats(self, start_date: str, end_date: str) -> Optional[ChannelStats]:
        """
        Get channel performance metrics.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            ChannelStats object or None if error.
        """
        if not _google_api_available or self.service is None:
            return None
        
        try:
            response = self.service.reports().query(
                ids='channel==MINE',
                metrics='views,estimatedMinutesWatched,subscribersGained',
                startDate=start_date,
                endDate=end_date
            ).execute()
            
            if not response.get('rows'):
                return None
            
            row = response['rows'][0]
            
            return ChannelStats(
                total_views=int(row[0]),
                watch_time_minutes=float(row[1]),
                subscribers_gained=int(row[2]),
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            if _google_api_available and _HttpError and isinstance(e, _HttpError):
                print(f"Error fetching channel stats: {e}")
            return None


# =============================================================================
# Pure Functions
# =============================================================================

def parse_stats_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse YouTube Analytics stats response into clean dict.
    
    Args:
        raw: Raw API response dict.
    
    Returns:
        Dictionary with parsed stats.
    """
    if not raw.get('rows'):
        return {}
    
    row = raw['rows'][0]
    
    return {
        'views': int(row[0]),
        'watch_time_minutes': float(row[1]),
        'avg_view_duration_seconds': float(row[2]),
        'avg_view_percentage': float(row[3]),
        'subscribers_gained': int(row[4]),
        'likes': int(row[5])
    }


def parse_retention_response(raw: Dict[str, Any]) -> List[Tuple[float, float]]:
    """
    Parse YouTube Analytics retention response into list of points.
    
    Args:
        raw: Raw API response dict.
    
    Returns:
        List of (elapsed_video_time_ratio, audience_watch_ratio) tuples.
    """
    points = []
    for row in raw.get('rows', []):
        points.append((float(row[0]), float(row[1])))
    
    return points


def parse_traffic_response(raw: Dict[str, Any]) -> Dict[str, int]:
    """
    Parse YouTube Analytics traffic sources response into dict.
    
    Args:
        raw: Raw API response dict.
    
    Returns:
        Dictionary mapping source_type to view_count.
    """
    sources = {}
    for row in raw.get('rows', []):
        source_type = row[0]
        view_count = int(row[1])
        sources[source_type] = view_count
    
    return sources


def format_retention_curve(points: List[Tuple[float, float]], width: int = 50) -> str:
    """
    Format retention curve as ASCII sparkline.
    
    Args:
        points: List of (elapsed_video_time_ratio, audience_watch_ratio) tuples.
        width: Width of sparkline in characters.
    
    Returns:
        ASCII sparkline string.
    """
    if not points:
        return "No retention data available"
    
    # Normalize points to fit width
    sparkline = []
    for i, (elapsed, audience) in enumerate(points):
        # Calculate position
        x_pos = int(elapsed * width)
        y_height = int(audience * 10)  # Scale to 10 lines max
        
        # Create sparkline character
        if y_height > 0:
            sparkline.append('█' * y_height)
        else:
            sparkline.append(' ')
    
    return ''.join(sparkline)


# =============================================================================
# CLI Interface
# =============================================================================

def print_video_stats(stats: VideoStats) -> None:
    """Print video statistics summary."""
    print(f"\n=== Video Stats: {stats.video_id} ===")
    print(f"Views: {stats.views:,}")
    print(f"Watch Time: {stats.watch_time_minutes:.1f} minutes")
    print(f"Avg View Duration: {stats.avg_view_duration_seconds:.1f} seconds")
    print(f"Avg View Percentage: {stats.avg_view_percentage:.1f}%")
    print(f"Subscribers Gained: {stats.subscribers_gained}")
    print(f"Likes: {stats.likes}")
    print(f"Period: {stats.start_date} to {stats.end_date}")


def print_retention_curve(points: List[RetentionPoint]) -> None:
    """Print retention curve as ASCII sparkline."""
    print(f"\n=== Retention Curve ===")
    if not points:
        print("No retention data available")
        return
    
    sparkline = format_retention_curve([(p.elapsed_video_time_ratio, p.audience_watch_ratio) for p in points])
    print(sparkline)
    
    # Print key points
    print(f"Start: {points[0].audience_watch_ratio:.1%}")
    print(f"Mid: {points[len(points)//2].audience_watch_ratio:.1%}")
    print(f"End: {points[-1].audience_watch_ratio:.1%}")


def print_traffic_sources(sources: Dict[str, int]) -> None:
    """Print traffic sources summary."""
    print(f"\n=== Traffic Sources ===")
    if not sources:
        print("No traffic source data available")
        return
    
    # Sort by view count
    sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
    
    for source, count in sorted_sources:
        print(f"{source}: {count:,} views")


def print_channel_stats(stats: ChannelStats) -> None:
    """Print channel statistics summary."""
    print(f"\n=== Channel Stats ===")
    print(f"Total Views: {stats.total_views:,}")
    print(f"Watch Time: {stats.watch_time_minutes:.1f} minutes")
    print(f"Subscribers Gained: {stats.subscribers_gained}")
    print(f"Period: {stats.start_date} to {stats.end_date}")


def load_library_cache() -> Dict[str, Any]:
    """Load YouTube library cache."""
    cache_path = ".youtube_cache/library.json"
    if not os.path.exists(cache_path):
        return {}
    
    with open(cache_path, 'r') as f:
        return json.load(f)


def get_series_videos(series_prefix: str) -> List[str]:
    """
    Get video IDs matching series prefix from library cache.
    
    Args:
        series_prefix: Series prefix (e.g., "eic")
    
    Returns:
        List of video IDs.
    """
    cache = load_library_cache()
    videos = cache.get('videos', [])
    
    matching_videos = []
    for video in videos:
        title = video.get('title', '').lower()
        if series_prefix.lower() in title:
            matching_videos.append(video['video_id'])
    
    return matching_videos


def save_to_cache(data: Dict[str, Any], cache_path: str) -> None:
    """Save analytics data to cache file."""
    cache_dir = Path(cache_path).parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Analytics Client")
    parser.add_argument('--video', help='YouTube video ID')
    parser.add_argument('--channel', action='store_true', help='Print 28-day channel summary')
    parser.add_argument('--series', help='Series prefix (e.g., "eic")')
    parser.add_argument('--save', action='store_true', help='Save data to .youtube_cache/analytics.json')
    parser.add_argument('--client-secret', help='Path to client_secret.json for OAuth')
    
    args = parser.parse_args()
    
    if not any([args.video, args.channel, args.series, args.save]):
        print("Error: Specify at least one option (--video, --channel, --series, --save)")
        sys.exit(1)
    
    analytics = YouTubeAnalytics(client_secret_path=args.client_secret)
    
    # Calculate date range (default: last 28 days)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=28)).strftime('%Y-%m-%d')
    
    cache_data = {}
    
    if args.video:
        stats = analytics.get_video_stats(args.video, start_date, end_date)
        if stats:
            print_video_stats(stats)
            cache_data['video_stats'] = {
                'video_id': stats.video_id,
                'views': stats.views,
                'watch_time_minutes': stats.watch_time_minutes,
                'avg_view_duration_seconds': stats.avg_view_duration_seconds,
                'avg_view_percentage': stats.avg_view_percentage,
                'subscribers_gained': stats.subscribers_gained,
                'likes': stats.likes,
                'start_date': stats.start_date,
                'end_date': stats.end_date
            }
            
            retention = analytics.get_retention_curve(args.video)
            print_retention_curve(retention)
            cache_data['retention'] = [
                {'elapsed': p.elapsed_video_time_ratio, 'audience': p.audience_watch_ratio}
                for p in retention
            ]
            
            traffic = analytics.get_traffic_sources(args.video)
            print_traffic_sources(traffic)
            cache_data['traffic_sources'] = traffic
    
    if args.channel:
        stats = analytics.get_channel_stats(start_date, end_date)
        if stats:
            print_channel_stats(stats)
            cache_data['channel_stats'] = {
                'total_views': stats.total_views,
                'watch_time_minutes': stats.watch_time_minutes,
                'subscribers_gained': stats.subscribers_gained,
                'start_date': stats.start_date,
                'end_date': stats.end_date
            }
    
    if args.series:
        video_ids = get_series_videos(args.series)
        if not video_ids:
            print(f"No videos found matching series prefix: {args.series}")
        else:
            print(f"\n=== Series: {args.series.upper()} ({len(video_ids)} videos) ===")
            series_stats = []
            for video_id in video_ids:
                stats = analytics.get_video_stats(video_id, start_date, end_date)
                if stats:
                    print(f"{stats.video_id}: {stats.views:,} views")
                    series_stats.append({
                        'video_id': stats.video_id,
                        'views': stats.views,
                        'avg_view_percentage': stats.avg_view_percentage
                    })
            cache_data['series_stats'] = series_stats
    
    if args.save:
        cache_path = ".youtube_cache/analytics.json"
        save_to_cache(cache_data, cache_path)
        print(f"\nData saved to {cache_path}")


if __name__ == '__main__':
    main()