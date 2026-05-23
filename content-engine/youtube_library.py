"""
YouTube Library Data Client

Pulls channel metadata, video library, and playlist data from YouTube Data API v3.
Uses gcloud ADC for authentication (same pattern as youtube_upload.py).
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

# Google API imports
try:
    from google.auth import default
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: Google API libraries not installed.")
    print("Run: pip install google-auth google-api-python-client google-auth-httplib2")
    sys.exit(1)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class YouTubeChannel:
    """YouTube channel metadata."""
    channel_id: str
    title: str
    description: str
    subscriber_count: int
    total_views: int
    video_count: int
    custom_url: Optional[str] = None


@dataclass
class YouTubeVideo:
    """YouTube video metadata."""
    video_id: str
    title: str
    description: str
    tags: List[str]
    publish_date: str
    status: str  # public, private, unlisted, scheduled
    duration: str  # ISO format (PT4M13S)
    thumbnail_url: str
    view_count: int
    like_count: int
    comment_count: int


@dataclass
class YouTubePlaylist:
    """YouTube playlist metadata."""
    playlist_id: str
    title: str
    description: str
    video_count: int
    video_ids: List[str]
    thumbnail_url: str


# =============================================================================
# API Client
# =============================================================================

class YouTubeLibrary:
    """Client for YouTube Data API v3 library data."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize YouTube library client.
        
        Args:
            api_key: Optional YouTube Data API v3 API key. If not provided, uses gcloud ADC.
        """
        try:
            if api_key:
                # Use API key for public data access
                self.service = build('youtube', 'v3', developerKey=api_key)
            else:
                # Use gcloud ADC for authenticated access
                credentials, project = default(
                    scopes=["https://www.googleapis.com/auth/youtube.readonly"]
                )
                self.service = build('youtube', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error during authentication: {e}")
            if api_key:
                print("Make sure the API key is valid and has YouTube Data API v3 enabled.")
            else:
                print("Make sure gcloud auth application-default login has been run with YouTube read scope.")
            sys.exit(1)
    
    def get_channel_metadata(self, channel_id: Optional[str] = None) -> Optional[YouTubeChannel]:
        """
        Get channel metadata for the authenticated user's channel or a specific channel.
        
        Args:
            channel_id: Optional YouTube channel ID. If not provided, uses mine=True.
        
        Returns:
            YouTubeChannel object or None if not found.
        """
        try:
            if channel_id:
                response = self.service.channels().list(
                    part='snippet,statistics',
                    id=channel_id
                ).execute()
            else:
                response = self.service.channels().list(
                    part='snippet,statistics',
                    mine=True
                ).execute()
            
            if not response.get('items'):
                return None
            
            channel_data = response['items'][0]
            snippet = channel_data.get('snippet', {})
            statistics = channel_data.get('statistics', {})
            
            return YouTubeChannel(
                channel_id=channel_data['id'],
                title=snippet.get('title', ''),
                description=snippet.get('description', ''),
                subscriber_count=int(statistics.get('subscriberCount', 0)),
                total_views=int(statistics.get('viewCount', 0)),
                video_count=int(statistics.get('videoCount', 0)),
                custom_url=snippet.get('customUrl')
            )
        except HttpError as e:
            print(f"Error fetching channel metadata: {e}")
            return None
    
    def get_video_library(self) -> List[YouTubeVideo]:
        """
        Get all videos from the authenticated user's channel.
        
        Returns:
            List of YouTubeVideo objects.
        """
        videos = []
        next_page_token = None
        
        try:
            while True:
                response = self.service.search().list(
                    part='snippet',
                    channelId=self.get_channel_metadata().channel_id if self.get_channel_metadata() else None,
                    maxResults=50,
                    order='date',
                    pageToken=next_page_token
                ).execute()
                
                for item in response.get('items', []):
                    video_id = item['id']['videoId']
                    snippet = item.get('snippet', {})
                    
                    # Get detailed video info including status
                    video_response = self.service.videos().list(
                        part='snippet,contentDetails,status,statistics',
                        id=video_id
                    ).execute()
                    
                    if video_response.get('items'):
                        video_data = video_response['items'][0]
                        video_snippet = video_data.get('snippet', {})
                        status = video_data.get('status', {})
                        statistics = video_data.get('statistics', {})
                        
                        videos.append(YouTubeVideo(
                            video_id=video_id,
                            title=video_snippet.get('title', ''),
                            description=video_snippet.get('description', ''),
                            tags=video_snippet.get('tags', []),
                            publish_date=video_snippet.get('publishedAt', ''),
                            status=status.get('privacyStatus', 'unknown'),
                            duration=video_data.get('contentDetails', {}).get('duration', ''),
                            thumbnail_url=video_snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                            view_count=int(statistics.get('viewCount', 0)),
                            like_count=int(statistics.get('likeCount', 0)),
                            comment_count=int(statistics.get('commentCount', 0))
                        ))
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
        
        except HttpError as e:
            print(f"Error fetching video library: {e}")
        
        return videos
    
    def get_playlists(self) -> List[YouTubePlaylist]:
        """
        Get all playlists from the authenticated user's channel.
        
        Returns:
            List of YouTubePlaylist objects.
        """
        playlists = []
        next_page_token = None
        
        try:
            while True:
                response = self.service.playlists().list(
                    part='snippet,contentDetails',
                    mine=True,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                for item in response.get('items', []):
                    snippet = item.get('snippet', {})
                    content_details = item.get('contentDetails', {})
                    
                    # Get playlist items to get video IDs
                    playlist_id = item['id']
                    video_ids = []
                    playlist_items_response = self.service.playlistItems().list(
                        part='contentDetails',
                        playlistId=playlist_id,
                        maxResults=50
                    ).execute()
                    
                    for playlist_item in playlist_items_response.get('items', []):
                        video_ids.append(playlist_item['contentDetails']['videoId'])
                    
                    playlists.append(YouTubePlaylist(
                        playlist_id=playlist_id,
                        title=snippet.get('title', ''),
                        description=snippet.get('description', ''),
                        video_count=int(content_details.get('itemCount', 0)),
                        video_ids=video_ids,
                        thumbnail_url=snippet.get('thumbnails', {}).get('default', {}).get('url', '')
                    ))
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
        
        except HttpError as e:
            print(f"Error fetching playlists: {e}")
        
        return playlists


# =============================================================================
# Pure Functions for Parsing
# =============================================================================

def parse_channel_response(raw: Dict[str, Any]) -> YouTubeChannel:
    """
    Parse YouTube API channel response into YouTubeChannel dataclass.
    
    Args:
        raw: Raw API response dict.
    
    Returns:
        YouTubeChannel object.
    """
    channel_data = raw.get('items', [{}])[0]
    snippet = channel_data.get('snippet', {})
    statistics = channel_data.get('statistics', {})
    
    return YouTubeChannel(
        channel_id=channel_data['id'],
        title=snippet.get('title', ''),
        description=snippet.get('description', ''),
        subscriber_count=int(statistics.get('subscriberCount', 0)),
        total_views=int(statistics.get('viewCount', 0)),
        video_count=int(statistics.get('videoCount', 0)),
        custom_url=snippet.get('customUrl')
    )


def parse_video_response(raw: Dict[str, Any]) -> YouTubeVideo:
    """
    Parse YouTube API video response into YouTubeVideo dataclass.
    
    Args:
        raw: Raw API response dict.
    
    Returns:
        YouTubeVideo object.
    """
    video_data = raw.get('items', [{}])[0]
    snippet = video_data.get('snippet', {})
    status = video_data.get('status', {})
    statistics = video_data.get('statistics', {})
    
    return YouTubeVideo(
        video_id=video_data['id'],
        title=snippet.get('title', ''),
        description=snippet.get('description', ''),
        tags=snippet.get('tags', []),
        publish_date=snippet.get('publishedAt', ''),
        status=status.get('privacyStatus', 'unknown'),
        duration=video_data.get('contentDetails', {}).get('duration', ''),
        thumbnail_url=snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
        view_count=int(statistics.get('viewCount', 0)),
        like_count=int(statistics.get('likeCount', 0)),
        comment_count=int(statistics.get('commentCount', 0))
    )


def parse_playlist_response(raw: Dict[str, Any]) -> YouTubePlaylist:
    """
    Parse YouTube API playlist response into YouTubePlaylist dataclass.
    
    Args:
        raw: Raw API response dict.
    
    Returns:
        YouTubePlaylist object.
    """
    item = raw.get('items', [{}])[0]
    snippet = item.get('snippet', {})
    content_details = item.get('contentDetails', {})
    
    return YouTubePlaylist(
        playlist_id=item['id'],
        title=snippet.get('title', ''),
        description=snippet.get('description', ''),
        video_count=int(content_details.get('itemCount', 0)),
        video_ids=[],  # Would need separate API call to get video IDs
        thumbnail_url=snippet.get('thumbnails', {}).get('default', {}).get('url', '')
    )


def format_duration(iso_duration: str) -> str:
    """
    Convert ISO duration format to human-readable format.
    PT4M13S -> 4:13
    
    Args:
        iso_duration: ISO 8601 duration string (e.g., PT4M13S).
    
    Returns:
        Human-readable duration string (e.g., "4:13").
    """
    if not iso_duration or not iso_duration.startswith('PT'):
        return iso_duration
    
    # Remove PT prefix
    duration = iso_duration[2:]
    
    # Parse hours, minutes, seconds
    hours = 0
    minutes = 0
    seconds = 0
    
    if 'H' in duration:
        h_parts = duration.split('H')
        hours = int(h_parts[0])
        duration = h_parts[1] if len(h_parts) > 1 else ''
    
    if 'M' in duration:
        m_parts = duration.split('M')
        minutes = int(m_parts[0])
        duration = m_parts[1] if len(m_parts) > 1 else ''
    
    if 'S' in duration:
        seconds = int(duration.replace('S', ''))
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    elif minutes > 0:
        return f"{minutes}:{seconds:02d}"
    else:
        return f"0:{seconds:02d}"


# =============================================================================
# CLI Interface
# =============================================================================

def print_channel_summary(channel: YouTubeChannel) -> None:
    """Print channel metadata summary."""
    print("\n=== Channel Summary ===\n")
    print(f"Channel: {channel.title}")
    print(f"Channel ID: {channel.channel_id}")
    print(f"Subscribers: {channel.subscriber_count:,}")
    print(f"Total Views: {channel.total_views:,}")
    print(f"Total Videos: {channel.video_count:,}")
    if channel.custom_url:
        print(f"Custom URL: youtube.com/{channel.custom_url}")
    print(f"\nDescription: {channel.description[:200]}...")


def print_video_library(videos: List[YouTubeVideo]) -> None:
    """Print video library as formatted table."""
    if not videos:
        print("No videos found in library.")
        return
    
    print(f"\n=== Video Library ({len(videos)} videos) ===\n")
    
    for video in videos:
        duration = format_duration(video.duration)
        print(f"{video.title}")
        print(f"  ID: {video.video_id}")
        print(f"  Published: {video.publish_date[:10]}")
        print(f"  Duration: {duration}")
        print(f"  Status: {video.status}")
        print(f"  Views: {video.view_count:,}")
        print(f"  Tags: {', '.join(video.tags[:3])}..." if len(video.tags) > 3 else f"  Tags: {', '.join(video.tags)}")
        print()


def print_playlists(playlists: List[YouTubePlaylist]) -> None:
    """Print playlist data."""
    if not playlists:
        print("No playlists found.")
        return
    
    print(f"\n=== Playlists ({len(playlists)} playlists) ===\n")
    
    for playlist in playlists:
        print(f"{playlist.title}")
        print(f"  ID: {playlist.playlist_id}")
        print(f"  Videos: {playlist.video_count}")
        print()


def save_to_cache(data: Dict[str, Any], cache_path: str) -> None:
    """Save library data to cache file."""
    cache_dir = Path(cache_path).parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Library Data Client")
    parser.add_argument('--channel', action='store_true', help='Print channel summary')
    parser.add_argument('--channel-id', help='YouTube channel ID (for public channels)')
    parser.add_argument('--videos', action='store_true', help='Print video library')
    parser.add_argument('--playlists', action='store_true', help='Print playlist data')
    parser.add_argument('--save', action='store_true', help='Save data to .youtube_cache/library.json')
    parser.add_argument('--api-key', help='YouTube Data API v3 API key (for public data access)')
    
    args = parser.parse_args()
    
    if not any([args.channel, args.videos, args.playlists, args.save]):
        print("Error: Specify at least one option (--channel, --videos, --playlists, --save)")
        sys.exit(1)
    
    # Get API key from CLI argument or environment variable
    api_key = args.api_key or os.getenv('YOUTUBE_API_KEY')
    
    library = YouTubeLibrary(api_key=api_key)
    
    cache_data = {}
    
    if args.channel:
        channel = library.get_channel_metadata(channel_id=args.channel_id)
        if channel:
            print_channel_summary(channel)
            cache_data['channel'] = {
                'channel_id': channel.channel_id,
                'title': channel.title,
                'description': channel.description,
                'subscriber_count': channel.subscriber_count,
                'total_views': channel.total_views,
                'video_count': channel.video_count,
                'custom_url': channel.custom_url
            }
    
    if args.videos:
        videos = library.get_video_library()
        print_video_library(videos)
        cache_data['videos'] = [
            {
                'video_id': v.video_id,
                'title': v.title,
                'description': v.description,
                'tags': v.tags,
                'publish_date': v.publish_date,
                'status': v.status,
                'duration': v.duration,
                'thumbnail_url': v.thumbnail_url,
                'view_count': v.view_count,
                'like_count': v.like_count,
                'comment_count': v.comment_count
            }
            for v in videos
        ]
    
    if args.playlists:
        playlists = library.get_playlists()
        print_playlists(playlists)
        cache_data['playlists'] = [
            {
                'playlist_id': p.playlist_id,
                'title': p.title,
                'description': p.description,
                'video_count': p.video_count,
                'video_ids': p.video_ids,
                'thumbnail_url': p.thumbnail_url
            }
            for p in playlists
        ]
    
    if args.save:
        cache_path = ".youtube_cache/library.json"
        save_to_cache(cache_data, cache_path)
        print(f"\nData saved to {cache_path}")


if __name__ == "__main__":
    main()
