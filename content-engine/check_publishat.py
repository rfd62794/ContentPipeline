#!/usr/bin/env python3
"""
Check specific videos for publishAt dates.
"""

import sys
from pathlib import Path
import yaml

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.youtube_auth import build_service

def check_publishat():
    """Check specific videos for publishAt dates."""
    scopes = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
    service = build_service('youtube', 'v3', scopes)
    
    # Load plan
    with open('reschedule_jun28_replan.yaml', 'r') as f:
        plan = yaml.safe_load(f)
    
    plan_titles = [item['title'] for item in plan['reschedules']]
    
    print("=== Checking publishAt for Plan Videos ===")
    
    try:
        # Get channel's uploads playlist
        channel_response = service.channels().list(
            part='contentDetails',
            mine=True
        ).execute()
        
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get all private videos
        next_page_token = None
        
        while True:
            playlist_response = service.playlistItems().list(
                part='contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            
            video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]
            
            if video_ids:
                videos_response = service.videos().list(
                    part='snippet,status',
                    id=','.join(video_ids)
                ).execute()
                
                for video_data in videos_response.get('items', []):
                    snippet = video_data.get('snippet', {})
                    status = video_data.get('status', {})
                    title = snippet.get('title', '')
                    
                    if title in plan_titles:
                        print(f"\nVideo: {title}")
                        print(f"  ID: {video_data['id']}")
                        print(f"  Privacy: {status.get('privacyStatus', '')}")
                        print(f"  PublishAt: {snippet.get('publishAt', 'NONE')}")
                        print(f"  PublishedAt: {snippet.get('publishedAt', 'NONE')}")
            
            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_publishat()
