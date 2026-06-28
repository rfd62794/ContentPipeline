#!/usr/bin/env python3
"""
Debug script to check what scheduled videos exist.
"""

import sys
from pathlib import Path

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.youtube_auth import build_service

def debug_scheduled_videos():
    """Debug scheduled videos fetch."""
    scopes = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
    service = build_service('youtube', 'v3', scopes)
    
    if not service:
        print("Failed to build service")
        return
    
    print("=== Debugging Scheduled Videos ===")
    
    try:
        # Get channel info
        channel_response = service.channels().list(
            part='contentDetails',
            mine=True
        ).execute()
        
        if not channel_response.get('items'):
            print("No channel found")
            return
        
        channel = channel_response['items'][0]
        uploads_playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']
        print(f"Channel ID: {channel['id']}")
        print(f"Uploads playlist: {uploads_playlist_id}")
        
        # Get all videos from uploads
        next_page_token = None
        total_videos = 0
        scheduled_count = 0
        private_count = 0
        
        while True:
            playlist_response = service.playlistItems().list(
                part='contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            
            video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]
            total_videos += len(video_ids)
            
            if video_ids:
                videos_response = service.videos().list(
                    part='snippet,status',
                    id=','.join(video_ids)
                ).execute()
                
                for video_data in videos_response.get('items', []):
                    snippet = video_data.get('snippet', {})
                    status = video_data.get('status', {})
                    title = snippet.get('title', '')
                    privacy = status.get('privacyStatus', '')
                    publish_at = snippet.get('publishAt', '')
                    
                    if privacy == 'private':
                        private_count += 1
                        if publish_at:
                            scheduled_count += 1
                            print(f"SCHEDULED: {title[:60]}")
                            print(f"  PublishAt: {publish_at}")
                            print(f"  Video ID: {video_data['id']}")
                            print()
                        else:
                            print(f"PRIVATE (not scheduled): {title[:60]}")
            
            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break
        
        print(f"\nSummary:")
        print(f"Total videos in uploads: {total_videos}")
        print(f"Private videos: {private_count}")
        print(f"Scheduled videos: {scheduled_count}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_scheduled_videos()
